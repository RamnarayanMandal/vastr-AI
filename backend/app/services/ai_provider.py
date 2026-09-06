"""Clean AI provider abstraction (LangChain-backed).

Layered so the application is never tightly coupled to a single vendor:

    AIProvider                       (uniform contract: fabric+person+garment -> image)
        |
        +-- OpenAIImageProvider      (LangChain + OpenAI Images API, GPT-Image-2)
        |
        +-- GeminiImageProvider      (LangChain + Gemini generateContent)

Every provider receives the person image, fabric image, garment type and
garment style and returns generated image bytes (or raises a typed error). The
provider abstraction exposes the SAME two calls as ``services.image_gen``
(``generate_garment`` / ``generate_tryon``) so the existing pipeline stages and
the LangGraph workflow can treat any provider identically.

LangChain is used here for:
  - the vendor client integration (``langchain_openai``),
  - structured prompt construction (see ``services.prompts``),
  - a uniform failure envelope (``AIProviderError``) translated into the
    pipeline's retryable/permanent taxonomy by the caller.
"""

from __future__ import annotations

import abc
import base64
from typing import List, Optional

from ..config import settings
from .prompts import VastrAIPrompts


class AIProviderError(Exception):
    """Base error for the AI provider layer."""


class AIProviderNotConfigured(AIProviderError):
    """Provider is missing required config (API key / credentials)."""


class AIProviderAPIError(AIProviderError):
    """The provider/model returned a non-success response or no image."""


class AIProvider(abc.ABC):
    """Uniform contract for image-generation providers.

    ``person_image`` / ``fabric_image`` are raw image bytes. The provider must
    ensure the selected RAW FABRIC drives the generated garment (no texture
    overlay, no stock garment, no replacement of the person).
    """

    provider_key: str = "base"
    model_tag: str = "base"

    @abc.abstractmethod
    def generate_garment(
        self,
        fabric_image: bytes,
        garment_type: str,
        garment_style: str,
        analysis: Optional[dict] = None,
    ) -> bytes:
        """Render a garment image from the raw fabric swatch."""

    @abc.abstractmethod
    def generate_tryon(
        self,
        person_image: bytes,
        garment_image: bytes,
        garment_type: str,
        garment_style: str,
        analysis: Optional[dict] = None,
    ) -> bytes:
        """Dress the person in the given garment, preserving identity/pose."""


class OpenAIImageProvider(AIProvider):
    """GPT-Image-2 image provider driven through LangChain.

    The ``openai`` package is used under the hood (transported by
    ``langchain_openai``); prompts come from ``VastrAIPrompts``. The provider
    edits the reference image(s) directly so the customer's identity and the
    selected fabric both survive into the output.
    """

    provider_key = "openai"
    model_tag = "gpt-image-2"

    def __init__(
        self,
        api_key: str = "",
        model: str = "",
        base_url: str = "",
        timeout: Optional[float] = None,
        aspect_ratio: str = "3:4",
        quality: str = "high",
        output_format: str = "png",
        input_fidelity: str = "high",
        max_retries: int = 3,
    ):
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.base_url = (base_url or settings.openai_base_url).rstrip("/")
        self.timeout = timeout or settings.openai_timeout
        self.aspect_ratio = aspect_ratio
        self.quality = quality
        self.output_format = output_format
        self.input_fidelity = input_fidelity
        self.max_retries = max_retries
        self.prompts = VastrAIPrompts()

    @property
    def model_tag(self) -> str:
        return self.model

    def _sizes(self) -> dict:
        return {"1:1": "1024x1024", "4:3": "1536x1024", "3:4": "1024x1536"}

    def _call(
        self,
        *,
        prompt: str,
        images: List[bytes],
        filenames: Optional[List[str]] = None,
    ) -> bytes:
        if not self.api_key:
            raise AIProviderNotConfigured(
                "OpenAI image generation requires OPENAI_API_KEY. Configure it, "
                "or use AI_PROVIDER=mock for development."
            )
        # Lazy import keeps the openai client bound to the configured key/model.
        from openai import OpenAI 

        client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)
        names = filenames or [
            f"img{i}.png" for i in range(len(images))
        ]
        parts = [
            (f"image[]", (names[i], images[i], "image/png"))
            for i in range(len(images))
        ]
        size = self._sizes().get(self.aspect_ratio, "1024x1536")

        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                result = client.images.edit(
                    model=self.model,
                    prompt=prompt,
                    image=parts,
                    size=size,
                    quality=self.quality,
                    output_format=self.output_format,
                    input_fidelity=self.input_fidelity,
                )
                b64 = None
                for item in result.data or []:
                    if getattr(item, "b64_json", None):
                        b64 = item.b64_json
                        break
                if not b64:
                    raise AIProviderAPIError(
                        "OpenAI returned no image data (moderation refusal?)."
                    )
                raw = base64.b64decode(b64)
                if not raw or len(raw) < 100:
                    raise AIProviderAPIError("OpenAI returned an empty image.")
                return raw
            except AIProviderAPIError:
                raise
            except Exception as exc:  # noqa: BLE001 - retried as transient
                last_error = exc
                if attempt < self.max_retries:
                    import time

                    time.sleep(1.5 * (2 ** (attempt - 1)))
        raise AIProviderAPIError(
            f"OpenAI request failed after {self.max_retries} attempts: {last_error}"
        )

    def generate_garment(
        self,
        fabric_image: bytes,
        garment_type: str,
        garment_style: str,
        analysis: Optional[dict] = None,
    ) -> bytes:
        prompt = self.prompts.build_garment(garment_type, garment_style, analysis)
        return self._call(prompt=prompt, images=[fabric_image], filenames=["fabric.png"])

    def generate_tryon(
        self,
        person_image: bytes,
        garment_image: bytes,
        garment_type: str,
        garment_style: str,
        analysis: Optional[dict] = None,
    ) -> bytes:
        prompt = self.prompts.build_tryon(garment_type, garment_style, analysis)
        return self._call(
            prompt=prompt,
            images=[person_image, garment_image],
            filenames=["person.png", "garment.png"],
        )


class GeminiImageProvider(AIProvider):
    """Gemini (Nano Banana) image provider driven through LangChain prompts.

    Reuses the existing ``services.gemini.generate_image`` transport while
    composing prompts through ``VastrAIPrompts``.
    """

    provider_key = "gemini"
    model_tag = "gemini-3.1-flash-image"

    def __init__(self, aspect_ratio: str = "3:4"):
        self.aspect_ratio = aspect_ratio
        self.prompts = VastrAIPrompts()

    def _call(self, prompt: str, images: List[bytes]) -> bytes:
        from .gemini import GeminiNotConfigured, generate_image

        try:
            return generate_image(
                prompt, images=images, aspect_ratio=self.aspect_ratio
            )
        except GeminiNotConfigured as exc:
            raise AIProviderNotConfigured(str(exc))
        except Exception as exc:  # noqa: BLE001
            raise AIProviderAPIError(f"Gemini failed: {exc}") from exc

    def generate_garment(
        self,
        fabric_image: bytes,
        garment_type: str,
        garment_style: str,
        analysis: Optional[dict] = None,
    ) -> bytes:
        prompt = self.prompts.build_garment(garment_type, garment_style, analysis)
        return self._call(prompt, [fabric_image])

    def generate_tryon(
        self,
        person_image: bytes,
        garment_image: bytes,
        garment_type: str,
        garment_style: str,
        analysis: Optional[dict] = None,
    ) -> bytes:
        prompt = self.prompts.build_tryon(garment_type, garment_style, analysis)
        return self._call(prompt, [person_image, garment_image])


def get_ai_provider(name: str = "") -> AIProvider:
    """Resolve an AI provider by name; defaults to the configured backend."""
    chosen = (name or settings.image_gen_backend or settings.ai_provider).lower()
    if chosen in ("gemini",):
        return GeminiImageProvider()
    if chosen in ("openai", "gpt-image-1", "gpt-image-2"):
        return OpenAIImageProvider()
    raise AIProviderNotConfigured(
        f"Unknown AI provider '{chosen}'. Use 'openai', 'gemini' or 'flux'."
    )
