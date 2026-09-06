"""Image-generation backend abstraction (Gemini / FLUX).

The complete raw-fabric -> garment -> person workflow is exactly two image
generation calls:

  1. fabric swatch -> garment representation   (``generate_garment``)
  2. person + garment -> try-on result          (``generate_tryon``)

A concrete ``ImageGenBackend`` implements both calls against a REAL image
model. Providers compose these calls through the pipeline stages, so swapping
the underlying model (Gemini API / self-hosted FLUX) is a factory/config
change - nothing else in the app moves.

Backends never fake or overlay the fabric: ``FluxImageGenBackend`` and
``GeminiImageGenBackend`` call a model. If the model is not configured they
raise ``ImageGenNotConfigured`` (mapped by the pipeline to an honest
``ProviderConfigurationError``).
"""

from __future__ import annotations

import abc
import base64
import io
import time
from typing import List, Optional

import httpx

from ..config import settings
from ..services.perf import ago_ms, perf


class ImageGenError(Exception):
    """Base error for image generation backends."""


class ImageGenNotConfigured(ImageGenError):
    """Backend is missing required config (API key, endpoint, auth)."""


class ImageGenAPIError(ImageGenError):
    """The backend returned a non-success response or no image."""


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def build_garment_prompt(
    garment_type: str,
    garment_style: str,
    analysis: Optional[dict],
) -> str:
    """Prompt that turns a raw fabric swatch into a flat garment image.

    Built with LangChain ``PromptTemplate`` (see ``services.prompts``) and
    seeded from the fabric analysis so the selected raw fabric drives the
    garment.
    """
    from .prompts import VastrAIPrompts

    return VastrAIPrompts().build_garment(garment_type, garment_style, analysis)


def build_tryon_prompt(
    garment_type: str,
    garment_style: str,
    analysis: Optional[dict],
) -> str:
    """Prompt that dresses the person in the generated garment (LangChain)."""
    from .prompts import VastrAIPrompts

    return VastrAIPrompts().build_tryon(garment_type, garment_style, analysis)


# ---------------------------------------------------------------------------
# Backend interface
# ---------------------------------------------------------------------------

class ImageGenBackend(abc.ABC):
    key: str = "base"
    model_tag: str = "base"

    @abc.abstractmethod
    def generate_garment(
        self,
        fabric: bytes,
        garment_type: str,
        garment_style: str,
        analysis: Optional[dict],
    ) -> bytes:
        """Render a garment image from the raw fabric swatch."""

    @abc.abstractmethod
    def generate_tryon(
        self,
        person: bytes,
        garment: bytes,
        garment_type: str,
        garment_style: str,
        analysis: Optional[dict],
    ) -> bytes:
        """Try the garment on the person while preserving identity/pose."""


# ---------------------------------------------------------------------------
# Gemini (Nano Banana) backend
# ---------------------------------------------------------------------------

class GeminiImageGenBackend(ImageGenBackend):
    key = "gemini"
    model_tag = "gemini-3.1-flash-image"

    def __init__(self, aspect_ratio: str = "3:4"):
        self.aspect_ratio = aspect_ratio

    def _generate(self, image_key: str, images: List[bytes], prompt: str) -> bytes:
        from .gemini import GeminiNotConfigured, generate_image

        try:
            return generate_image(
                prompt,
                images=images,
                aspect_ratio=self.aspect_ratio,
            )
        except GeminiNotConfigured as exc:
            raise ImageGenNotConfigured(str(exc))
        except Exception as exc:
            raise ImageGenAPIError(f"Gemini failed ({image_key}): {exc}") from exc

    def generate_garment(
        self,
        fabric: bytes,
        garment_type: str,
        garment_style: str,
        analysis: Optional[dict],
    ) -> bytes:
        return self._generate(
            "garment",
            [fabric],
            build_garment_prompt(garment_type, garment_style, analysis),
        )

    def generate_tryon(
        self,
        person: bytes,
        garment: bytes,
        garment_type: str,
        garment_style: str,
        analysis: Optional[dict],
    ) -> bytes:
        return self._generate(
            "tryon",
            [person, garment],
            build_tryon_prompt(garment_type, garment_style, analysis),
        )


# ---------------------------------------------------------------------------
# FLUX backend (self-hosted / hosted FLUX-compatible image API)
# ---------------------------------------------------------------------------
#
# Contract (documented in AI_MODEL.md): a single endpoint that takes
# reference images (JSON base64) + a prompt and returns the generated image:
#
#   POST {FLUX_ENDPOINT}
#   {
#     "task": "garment" | "tryon",
#     "model": "<FLUX_MODEL>",
#     "prompt": "...",
#     "reference_images": ["<base64 image>", ...]
#   }
#   200 -> {"image": "<base64 output>"}   (or raw image bytes)
#
# Without FLUX_ENDPOINT the backend fails honestly with ImageGenNotConfigured.

class FluxImageGenBackend(ImageGenBackend):
    key = "flux"

    def __init__(
        self,
        endpoint: str = "",
        api_key: str = "",
        model: str = "",
        timeout: Optional[float] = None,
    ):
        self.endpoint = endpoint or settings.flux_endpoint
        self.api_key = api_key or settings.flux_api_key
        self.model = model or settings.flux_model
        self.timeout = timeout or settings.flux_timeout

    @property
    def model_tag(self) -> str:
        return self.model

    def _call(self, task: str, prompt: str, images: List[bytes]) -> bytes:
        if not self.endpoint:
            raise ImageGenNotConfigured(
                "FLUX generation requires FLUX_ENDPOINT (a FLUX-compatible "
                "image API). Configure FLUX_ENDPOINT, or use AI_PROVIDER=mock "
                "for development."
            )
        payload = {
            "task": task,
            "model": self.model,
            "prompt": prompt,
            "reference_images": [
                base64.b64encode(img).decode("ascii") for img in images
            ],
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            resp = httpx.post(
                self.endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise ImageGenAPIError(f"FLUX request failed: {exc}")

        if resp.status_code != 200:
            raise ImageGenAPIError(
                f"FLUX API error {resp.status_code}: {resp.text[:300]}"
            )

        content_type = resp.headers.get("content-type", "")
        if "json" not in content_type and resp.content:
            img = resp.content
        else:
            try:
                data = resp.json()
            except ValueError:
                raise ImageGenAPIError("FLUX returned an unparseable response.")
            img = data.get("image") or data.get("b64_json") or data.get("data")
            if not img:
                raise ImageGenAPIError("FLUX returned no image data.")
            try:
                img = base64.b64decode(img)
            except Exception as exc:
                raise ImageGenAPIError(f"FLUX returned invalid base64: {exc}")

        if not img or len(img) < 100:
            raise ImageGenAPIError("FLUX returned an empty image.")
        return img

    def generate_garment(
        self,
        fabric: bytes,
        garment_type: str,
        garment_style: str,
        analysis: Optional[dict],
    ) -> bytes:
        return self._call(
            "garment",
            build_garment_prompt(garment_type, garment_style, analysis),
            [fabric],
        )

    def generate_tryon(
        self,
        person: bytes,
        garment: bytes,
        garment_type: str,
        garment_style: str,
        analysis: Optional[dict],
    ) -> bytes:
        return self._call(
            "tryon",
            build_tryon_prompt(garment_type, garment_style, analysis),
            [person, garment],
        )


# ---------------------------------------------------------------------------
# OpenAI backend (Images API /image edits, gpt-image-2)
# ---------------------------------------------------------------------------
#
# Contract: POST {OPENAI_BASE_URL}/images/edits as multipart/form-data:
#
#   text fields:
#     model=gpt-image-2
#     prompt=...
#     size=1024x1536                    # 3:4 aspect
#     quality=high
#     output_format=png
#     input_fidelity=high               # preserve facial features
#   file parts (one per reference image):
#     image[]=<image bytes> (filename + content_type required)
#
#   200 -> {"data": [{"b64_json": "<base64 output>"}]}
#   gpt-image models always return b64_json (do NOT send response_format).
#
# Without OPENAI_API_KEY the backend fails honestly with ImageGenNotConfigured.

_SIZES = {
    "1:1": "1024x1024",
    "4:3": "1536x1024",
    "3:4": "1024x1536",
}


class OpenAIImageGenBackend(ImageGenBackend):
    key = "openai"

    def __init__(
        self,
        api_key: str = "",
        model: str = "",
        base_url: str = "",
        timeout: Optional[float] = None,
        quality: str = "high",
        output_format: str = "png",
        aspect_ratio: str = "3:4",
        input_fidelity: str = "high",
        max_retries: int = 3,
    ):
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.base_url = (base_url or settings.openai_base_url).rstrip("/")
        self.timeout = timeout or settings.openai_timeout
        self.quality = quality
        self.output_format = output_format
        self.aspect_ratio = aspect_ratio
        self.input_fidelity = input_fidelity
        self.max_retries = max_retries

    @property
    def model_tag(self) -> str:
        return self.model

    def _call(self, task: str, prompt: str, images: List[bytes]) -> bytes:
        if not self.api_key:
            raise ImageGenNotConfigured(
                "OpenAI image generation requires OPENAI_API_KEY to be set. "
                "Configure OPENAI_API_KEY, or use AI_PROVIDER=mock for development."
            )
        names = {
            0: "fabric.png" if task == "garment" else "person.png",
            1: "garment.png",
        }
        files = []
        for i, img in enumerate(images):
            files.append(("image[]", (names.get(i, f"image{i}.png"), img, "image/png")))
        data = {
            "model": self.model,
            "prompt": prompt,
            "size": _SIZES.get(self.aspect_ratio, "1024x1536"),
            "quality": self.quality,
            "output_format": self.output_format,
            "input_fidelity": self.input_fidelity,
        }
        url = f"{self.base_url}/images/edits"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        resp = None
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = httpx.post(
                    url,
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=self.timeout,
                )
            except httpx.HTTPError as exc:
                last_error = exc
                resp = None
            if resp is not None and resp.status_code not in (429,) and resp.status_code < 500:
                break
            # Transient transport errors, rate limits and 5xx: back off and retry.
            # Image calls are long and connections can be dropped mid-transfer.
            if attempt < self.max_retries:
                time.sleep(1.5 * (2 ** (attempt - 1)))
        if resp is None:
            raise ImageGenAPIError(
                f"OpenAI request failed after {self.max_retries} attempts: {last_error}"
            )

        if resp.status_code != 200:
            detail = ""
            try:
                detail = resp.json().get("error", {}).get("message", "")
            except Exception:
                pass
            raise ImageGenAPIError(
                f"OpenAI API error {resp.status_code}: {detail or resp.text[:300]}"
            )

        try:
            result = resp.json()
        except ValueError:
            raise ImageGenAPIError("OpenAI returned an unparseable response.")

        b64 = None
        for item in result.get("data", []) or []:
            if item.get("b64_json"):
                b64 = item["b64_json"]
                break
        if not b64 and result.get("data"):
            b64 = result["data"][0].get("b64_json")
        if not b64:
            raise ImageGenAPIError("OpenAI returned no image data (moderation refusal?).")
        try:
            img = base64.b64decode(b64)
        except Exception as exc:
            raise ImageGenAPIError(f"OpenAI returned invalid base64: {exc}")
        if not img:
            raise ImageGenAPIError("OpenAI returned an empty image.")
        return img

    def generate_garment(
        self,
        fabric: bytes,
        garment_type: str,
        garment_style: str,
        analysis: Optional[dict],
    ) -> bytes:
        return self._call(
            "garment",
            build_garment_prompt(garment_type, garment_style, analysis),
            [fabric],
        )

    def generate_tryon(
        self,
        person: bytes,
        garment: bytes,
        garment_type: str,
        garment_style: str,
        analysis: Optional[dict],
    ) -> bytes:
        return self._call(
            "tryon",
            build_tryon_prompt(garment_type, garment_style, analysis),
            [person, garment],
        )


# ---------------------------------------------------------------------------
# OpenRouter backend (dedicated Image API, e.g. meta/muse-image)
# ---------------------------------------------------------------------------
#
# Contract (see https://openrouter.ai/docs/api/api-reference/images):
#   POST {OPENROUTER_BASE_URL}/images     (JSON body, OpenAI-compatible shape)
#   {
#     "model": "<provider/model slug>",
#     "prompt": "...",
#     "input_references": [             # reference images (base64 data URLs)
#       { "type": "image_url", "image_url": { "url": "data:image/png;base64,..." } }
#     ],
#     "aspect_ratio": "3:4"
#   }
#   200 -> {"data": [{"b64_json": "<base64 output>"}]}
#
# Without OPENROUTER_API_KEY the backend fails honestly with
# ImageGenNotConfigured - it never fakes a result.

class OpenRouterImageGenBackend(ImageGenBackend):
    key = "openrouter"

    def __init__(
        self,
        api_key: str = "",
        model: str = "",
        base_url: str = "",
        timeout: Optional[float] = None,
        aspect_ratio: str = "3:4",
        max_retries: int = 2,
        fallback_model: str = "",
        num_images: Optional[int] = None,
    ):
        self.api_key = api_key or settings.openrouter_api_key
        self.model = (model or settings.openrouter_model or "qwen/qwen-image-3").strip()
        self.fallback_model = (fallback_model or settings.openrouter_fallback_model or "").strip()
        self.base_url = (base_url or settings.openrouter_base_url).rstrip("/")
        self.timeout = timeout or settings.openrouter_timeout
        self.aspect_ratio = aspect_ratio
        self.max_retries = max(1, int(max_retries))
        self.num_images = max(1, int(num_images if num_images is not None else settings.openrouter_num_images))
        self.model_used = self.model

    @property
    def model_tag(self) -> str:
        return self.model_used or self.model

    def _data_url(self, img: bytes) -> str:
        from PIL import Image

        mime = "image/jpeg"
        try:
            with Image.open(io.BytesIO(img)) as im:
                # Cap at 1280px to keep API cost constant, but preserve the
                # source format when safe so fine checks/stripes/prints are not
                # destroyed by a second lossy JPEG encode.
                was_png = im.format == "PNG"
                im.thumbnail((1280, 1280))
                if im.mode not in ("RGB",):
                    im = im.convert("RGB")
                buf = io.BytesIO()
                if was_png:
                    im.save(buf, "PNG", optimize=True)
                    mime = "image/png"
                else:
                    im.save(buf, "JPEG", quality=90)
                img = buf.getvalue()
        except Exception:
            pass
        return "data:" + mime + ";base64," + base64.b64encode(img).decode("ascii")

    def _should_fallback(self, exc: Exception) -> bool:
        text = str(exc).lower()
        return bool(
            self.fallback_model
            and self.fallback_model != self.model
            and (
                "model" in text and ("not found" in text or "unknown" in text or "unavailable" in text or "not available" in text or "unsupported" in text)
                or "404" in text
                or "422" in text
            )
        )

    def _call_with_model(self, model: str, prompt: str, images: List[bytes], task: str = "") -> bytes:
        enc_t = time.perf_counter()
        references = [
            {"type": "image_url", "image_url": {"url": self._data_url(img)}}
            for img in images
        ]
        perf(
            "ai_input_encode_end",
            task=task,
            model=model,
            duration_ms=round(ago_ms(enc_t), 1),
            input_images=len(images),
        )
        payload = {
            "model": model,
            "prompt": prompt,
            "input_references": references,
            "aspect_ratio": self.aspect_ratio,
            "num_images": self.num_images,
        }
        url = f"{self.base_url}/images"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        print(
            f"[AI][REQUEST] model={model} size={self.aspect_ratio} "
            f"input_images={len(images)} output_images={self.num_images}",
            flush=True,
        )
        resp = None
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            att_t = time.perf_counter()
            try:
                resp = httpx.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )
                http_err = ""
            except httpx.HTTPError as exc:
                last_error = exc
                resp = None
                http_err = f"{type(exc).__name__}: {exc}"
            perf(
                "ai_http_attempt_end",
                task=task,
                model=model,
                attempt=attempt,
                duration_ms=round(ago_ms(att_t), 1),
                status=resp.status_code if resp is not None else None,
                error=http_err,
            )
            if resp is not None and resp.status_code not in (429,) and resp.status_code < 500:
                break
            if attempt < self.max_retries:
                sleep_s = 1.5 * (2 ** (attempt - 1))
                perf("ai_retry_backoff", task=task, model=model, attempt=attempt, sleep_s=sleep_s)
                time.sleep(sleep_s)
        if resp is None:
            raise ImageGenAPIError(
                f"OpenRouter request failed after {self.max_retries} attempts: {last_error}"
            )

        if resp.status_code != 200:
            detail = ""
            try:
                detail = resp.json().get("error", {}).get("message", "")
            except Exception:
                pass
            error_text = f"OpenRouter API error {resp.status_code}: {detail or resp.text[:300]}"
            raise ImageGenAPIError(error_text)

        try:
            result = resp.json()
        except ValueError:
            raise ImageGenAPIError("OpenRouter returned an unparseable response.")

        dec_t = time.perf_counter()
        b64 = None
        for item in result.get("data", []) or []:
            if item.get("b64_json"):
                b64 = item["b64_json"]
                break
        if not b64 and result.get("data"):
            b64 = result["data"][0].get("b64_json")
        if not b64:
            raise ImageGenAPIError("OpenRouter returned no image data.")
        try:
            img = base64.b64decode(b64)
        except Exception as exc:
            raise ImageGenAPIError(f"OpenRouter returned invalid base64: {exc}")
        if not img:
            raise ImageGenAPIError("OpenRouter returned an empty image.")
        perf(
            "ai_response_decode_end",
            task=task,
            model=model,
            duration_ms=round(ago_ms(dec_t), 1),
            bytes=len(img),
            output_images=1,
        )
        usage = result.get("usage") or {}
        cost = usage.get("cost")
        if cost is not None:
            print(
                f"[AI][COST] model={model} input_images={len(images)} "
                f"output_images=1 cost_usd={cost}",
                flush=True,
            )
        self.model_used = model
        return img

    def _call(self, task: str, prompt: str, images: List[bytes]) -> bytes:
        if not self.api_key:
            raise ImageGenNotConfigured(
                "OpenRouter image generation requires OPENROUTER_API_KEY. "
                "Configure OPENROUTER_API_KEY, or use AI_PROVIDER=mock "
                "for development."
            )

        candidates = [self.model]
        if self.fallback_model and self.fallback_model not in candidates:
            candidates.append(self.fallback_model)

        last_error = None
        for index, model_name in enumerate(candidates):
            if index > 0:
                perf("ai_fallback_used", task=task, model=self.model, fallback=model_name)
            try:
                return self._call_with_model(model_name, prompt, images, task=task)
            except ImageGenAPIError as exc:
                last_error = exc
                if index == 0 and self._should_fallback(exc):
                    continue
                raise
        raise ImageGenAPIError(f"OpenRouter request failed after fallback attempt: {last_error}")

    def generate_garment(
        self,
        fabric: bytes,
        garment_type: str,
        garment_style: str,
        analysis: Optional[dict],
    ) -> bytes:
        return self._call(
            "garment",
            build_garment_prompt(garment_type, garment_style, analysis),
            [fabric],
        )

    def generate_tryon(
        self,
        person: bytes,
        garment: bytes,
        garment_type: str,
        garment_style: str,
        analysis: Optional[dict],
    ) -> bytes:
        return self._call(
            "tryon",
            build_tryon_prompt(garment_type, garment_style, analysis),
            [person, garment],
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_image_gen_backend(name: str = "") -> ImageGenBackend:
    """Resolve a backend by name, defaulting to the configured provider."""
    chosen = (name or settings.image_gen_backend or settings.ai_provider).lower()
    if chosen == "gemini":
        return GeminiImageGenBackend()
    if chosen == "flux":
        return FluxImageGenBackend()
    if chosen in ("openai", "gpt-image-1"):
        return OpenAIImageGenBackend()
    if chosen == "openrouter":
        return OpenRouterImageGenBackend()
    raise ImageGenNotConfigured(
        f"Unknown image generation backend '{chosen}'. Use 'gemini', 'flux', "
        f"'openai' or 'openrouter'."
    )