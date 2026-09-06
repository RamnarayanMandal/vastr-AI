from __future__ import annotations

import abc
import io
import json
import uuid
from dataclasses import dataclass, field as dc_field
from typing import List, Optional

import httpx

from ..config import settings
from .image_gen import (
    GeminiImageGenBackend,
    ImageGenAPIError,
    ImageGenBackend,
    ImageGenError,
    ImageGenNotConfigured,
)
from .imagekit import download_url, upload_bytes


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class TryOnError(Exception):
    """Base error for the AI try-on pipeline."""

    retryable: bool = True


class RetryableTryOnError(TryOnError):
    """Transient failure (model timeout, upload hiccup) - safe to retry."""


class PermanentTryOnError(TryOnError):
    """Permanent failure (bad input, missing configuration) - do not retry."""

    retryable: bool = False


class InputValidationError(PermanentTryOnError):
    """The inputs are unusable (undownloadable, invalid image bytes)."""


class ProviderConfigurationError(PermanentTryOnError):
    """The provider is missing required configuration (e.g. an endpoint)."""


class FabricGenerationFailed(RetryableTryOnError):
    """Fabric -> garment generation failed during the pipeline run."""


class TryOnComposeFailed(RetryableTryOnError):
    """Virtual try-on composition failed."""


class QualityCheckFailed(RetryableTryOnError):
    """The generated image failed quality validation."""


class UploadFailed(RetryableTryOnError):
    """The generated image could not be uploaded/stored."""


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------

@dataclass
class TryOnInput:
    person_image_url: str
    fabric_image_url: str
    garment_type: str
    garment_style: str
    gender: Optional[str] = None


@dataclass
class FabricAnalysis:
    dominant_hex: str
    palette: List[str]
    has_pattern: bool
    brightness: float
    variance: float
    description: str

    def to_dict(self) -> dict:
        return {
            "dominant_hex": self.dominant_hex,
            "palette": self.palette,
            "has_pattern": self.has_pattern,
            "brightness": round(self.brightness, 3),
            "variance": round(self.variance, 2),
            "description": self.description,
        }


@dataclass
class PipelineContext:
    input_: TryOnInput
    provider: str
    person_bytes: Optional[bytes] = None
    fabric_bytes: Optional[bytes] = None
    fabric_analysis: Optional[FabricAnalysis] = None
    garment_bytes: Optional[bytes] = None
    result_bytes: Optional[bytes] = None
    identity_score: Optional[float] = None
    result_url: Optional[str] = None
    stage_log: List[dict] = dc_field(default_factory=list)

    def log(self, stage: str, status: str, note: str = "") -> None:
        self.stage_log.append({"stage": stage, "status": status, "note": note})


# ---------------------------------------------------------------------------
# Analysis / synthesis helpers (GPU-free, Pillow only)
# ---------------------------------------------------------------------------

def _hex(pixel) -> str:
    r, g, b = int(pixel[0]), int(pixel[1]), int(pixel[2])
    return "#%02x%02x%02x" % (r, g, b)


def _variance(pixels) -> float:
    n = len(pixels)
    if n == 0:
        return 0.0
    mean = [sum(p[i] for p in pixels) / n for i in range(3)]
    total = 0.0
    for p in pixels:
        total += ((p[0] - mean[0]) ** 2 + (p[1] - mean[1]) ** 2 + (p[2] - mean[2]) ** 2) / 3
    return total / n


def synthesize_person_bytes(size: tuple = (320, 400)) -> bytes:
    """GPU-free placeholder 'customer' used by the mock provider offline."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", size, (235, 228, 218))
    d = ImageDraw.Draw(img)
    cx = size[0] // 2
    d.ellipse([cx - 34, 30, cx + 34, 98], fill=(168, 148, 130))
    d.rectangle([cx - 70, 100, cx + 70, 250], fill=(201, 169, 106))
    d.rectangle([cx - 62, 252, cx - 12, 380], fill=(90, 96, 108))
    d.rectangle([cx + 12, 252, cx + 62, 380], fill=(90, 96, 108))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return buf.getvalue()


def synthesize_fabric_bytes(color: tuple = (58, 131, 200), size: tuple = (256, 256)) -> bytes:
    """Plain 'swatch' used by the mock provider offline."""
    from PIL import Image

    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return buf.getvalue()


def _require_decodable(data: bytes, what: str) -> None:
    from PIL import Image

    try:
        with Image.open(io.BytesIO(data)) as im:
            im.verify()
    except Exception:
        raise InputValidationError(f"The {what} is not a valid image.")


def analyze_fabric(fabric_bytes: bytes) -> FabricAnalysis:
    from PIL import Image

    img = Image.open(io.BytesIO(fabric_bytes)).convert("RGB")
    small = img.resize((64, 64))
    pixels = list(small.getdata())
    q = small.quantize(colors=5, method=Image.Quantize.MEDIANCUT)
    flat_palette = q.getpalette() or []
    counts = sorted(q.getcolors(maxcolors=100000) or [], reverse=True)

    def _pal_rgb(idx: int) -> tuple:
        base = idx * 3
        if base + 2 < len(flat_palette):
            return (flat_palette[base], flat_palette[base + 1], flat_palette[base + 2])
        return (128, 128, 128)

    dominant_rgb = _pal_rgb(counts[0][1]) if counts else (128, 128, 128)
    palette_colors = [_pal_rgb(idx) for _, idx in counts[:3]]
    variance = _variance(pixels)
    brightness = sum((p[0] + p[1] + p[2]) / 3 for p in pixels) / len(pixels) / 255.0
    has_pattern = variance > 900.0
    shade = "bright" if brightness > 0.6 else "dark"
    description = f"{shade} {"patterned" if has_pattern else "solid"} fabric"
    if len(palette_colors) > 1 and has_pattern:
        description += f" ({len(palette_colors)} tones)"
    description += "."
    return FabricAnalysis(
        dominant_hex=_hex(dominant_rgb),
        palette=[_hex(c) for c in palette_colors],
        has_pattern=has_pattern,
        brightness=brightness,
        variance=variance,
        description=description,
    )


def identity_metrics(person_bytes: bytes, result_bytes: bytes) -> float:
    """Structural overlap of the face region between source and result (0-1).

    The face band is the top-central crop. Two identical crops yield ~1.0.
    """
    from PIL import Image

    if not person_bytes or not result_bytes:
        return 0.0
    try:
        pa = Image.open(io.BytesIO(person_bytes)).convert("L")
        ra = Image.open(io.BytesIO(result_bytes)).convert("L")
    except Exception:
        return 0.0
    w, h = pa.size
    l, r = int(w * 0.2), int(w * 0.8)
    t, b = int(h * 0.03), int(h * 0.38)
    crop_p = pa.crop((l, t, r, b)).resize((48, 48))
    if ra.width != w:
        ra = ra.resize((w, h))
    crop_r = ra.crop((l, t, r, b)).resize((48, 48))
    sp = list(crop_p.getdata())
    sr = list(crop_r.getdata())
    if not sp or len(sp) != len(sr):
        return 0.0
    mad = sum(abs(a - b) for a, b in zip(sp, sr)) / len(sp)
    return max(0.0, 1.0 - mad / 255.0)


def _draw_garment_mask(d, W: int, H: int, garment_type: str) -> None:
    g = (garment_type or "").lower()
    if g in ("pant", "pants", "jeans", "palazzo", "short_pant", "shorts"):
        d.rectangle([44, 40, 116, 300], fill=255)
        d.rectangle([140, 40, 212, 300], fill=255)
        d.rectangle([40, 30, 216, 70], fill=255)
    elif g in ("saree", "dupatta", "lehenga"):
        d.polygon([(30, 24), (226, 24), (186, 300), (60, 300)], fill=255)
    elif g in ("dress", "frock", "kurti", "kurta", "ethnic_wear"):
        d.polygon([(66, 26), (190, 26), (210, 260), (46, 260)], fill=255)
    else:
        d.rectangle([44, 30, 212, 230], fill=255)
        d.rectangle([44, 30, 128, 92], fill=255)
        d.rectangle([128, 30, 212, 92], fill=255)


def _mock_garment_panel(fabric_bytes: bytes, analysis: FabricAnalysis, garment_type: str) -> bytes:
    """Build a flat garment panel from the fabric texture (development only)."""
    from PIL import Image, ImageDraw

    W, H = 256, 320
    canvas = Image.new("RGB", (W, H), (250, 248, 245))
    tile = Image.open(io.BytesIO(fabric_bytes)).convert("RGB").resize((W, H))
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    _draw_garment_mask(d, W, H, garment_type)
    panel = Image.new("RGB", (W, H), (0, 0, 0))
    panel.paste(tile, (0, 0))
    canvas.paste(panel, (0, 0), mask)
    d2 = ImageDraw.Draw(canvas)
    d2.text((10, 8), analysis.description[:30], fill=(120, 118, 114))
    buf = io.BytesIO()
    canvas.save(buf, "JPEG", quality=88)
    return buf.getvalue()


def _mock_tryon_compose(person_bytes: bytes, garment_bytes: bytes, garment_type: str) -> bytes:
    """Place the garment panel over the person's torso. The person image stays
    the base of the composite, so the face and identity are always preserved."""
    from PIL import Image, ImageDraw

    person = Image.open(io.BytesIO(person_bytes)).convert("RGB")
    w, h = person.size
    garment = Image.open(io.BytesIO(garment_bytes)).convert("RGB")
    gw, gh = garment.size
    if (garment_type or "").lower() in ("pant", "pants", "jeans", "palazzo", "short_pant", "shorts"):
        top = int(h * 0.42)
    else:
        top = int(h * 0.18)
    gw_target = int(w * 0.72)
    gh_target = max(1, int(gw_target * gh / gw))
    garment = garment.resize((gw_target, gh_target))
    mask = Image.new("L", garment.size, 120)
    person.paste(garment, ((w - gw_target) // 2, top), mask)
    draw = ImageDraw.Draw(person)
    draw.rectangle([0, h - 44, w, h], fill=(13, 11, 26))
    draw.text((w // 2 - 64, h - 34), "DEMO PREVIEW", fill=(201, 169, 106))
    buf = io.BytesIO()
    person.save(buf, "JPEG", quality=90)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

class PipelineStage(abc.ABC):
    stage_key: str = "stage"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        raise NotImplementedError


class ValidateInputsStage(PipelineStage):
    stage_key = "validate"

    def __init__(self, allow_synthesis: bool = False):
        self.allow_synthesis = allow_synthesis

    def run(self, ctx: PipelineContext) -> PipelineContext:
        inp = ctx.input_
        if not (inp.garment_type and inp.garment_style):
            raise InputValidationError("Garment type and style are required.")
        if inp.gender and inp.gender.upper() not in ("MEN", "WOMEN", "KIDS"):
            raise InputValidationError(f"Unknown gender '{inp.gender}'.")

        person_bytes = download_url(inp.person_image_url)
        if person_bytes is None:
            if self.allow_synthesis:
                ctx.person_bytes = synthesize_person_bytes()
            else:
                raise InputValidationError("Could not download the customer photo.")
        else:
            _require_decodable(person_bytes, "customer photo")
            ctx.person_bytes = person_bytes

        fabric_bytes = download_url(inp.fabric_image_url)
        if fabric_bytes is None:
            if self.allow_synthesis:
                ctx.fabric_bytes = synthesize_fabric_bytes()
            else:
                raise InputValidationError("Could not download the fabric photo.")
        else:
            _require_decodable(fabric_bytes, "fabric photo")
            ctx.fabric_bytes = fabric_bytes

        return ctx


class AnalyzeFabricStage(PipelineStage):
    stage_key = "analyze_fabric"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        ctx.fabric_analysis = analyze_fabric(ctx.fabric_bytes)
        return ctx


class GarmentConstructionStage(PipelineStage):
    """Build a garment representation from the fabric (abstract)."""

    stage_key = "construct_garment"

    @abc.abstractmethod
    def build_garment(self, ctx: PipelineContext) -> bytes: ...

    def run(self, ctx: PipelineContext) -> PipelineContext:
        ctx.garment_bytes = self.build_garment(ctx)
        return ctx


class MockGarmentConstructionStage(GarmentConstructionStage):
    """Flat garment panel sampled from the fabric texture (development only)."""

    def build_garment(self, ctx: PipelineContext) -> bytes:
        return _mock_garment_panel(ctx.fabric_bytes, ctx.fabric_analysis, ctx.input_.garment_type)


class HttpGarmentConstructionStage(GarmentConstructionStage):
    """Ask a fabric -> garment generation service to build the garment.

    Requires AI_GARMENT_GENERATION_ENDPOINT. Fails honestly otherwise.
    """

    def __init__(self, endpoint: str = ""):
        self.endpoint = endpoint or settings.garment_generation_endpoint

    def build_garment(self, ctx: PipelineContext) -> bytes:
        if not self.endpoint:
            raise ProviderConfigurationError(
                "Fabric-to-garment generation requires AI_GARMENT_GENERATION_ENDPOINT. "
                "Point it at a fabric->garment model service, or use AI_PROVIDER=mock for development."
            )
        try:
            resp = httpx.post(
                self.endpoint,
                files={"fabric": ("fabric.jpg", ctx.fabric_bytes, "image/jpeg")},
                data={
                    "garment_type": ctx.input_.garment_type,
                    "garment_style": ctx.input_.garment_style,
                    "fabric_analysis": json.dumps(ctx.fabric_analysis.to_dict()),
                },
                timeout=180,
            )
            resp.raise_for_status()
            data: bytes = resp.content
        except Exception as exc:
            raise FabricGenerationFailed(f"Garment generation service error: {exc}")
        if not data or len(data) < 100:
            raise FabricGenerationFailed("Garment generation returned an empty image.")
        _require_decodable(data, "generated garment")
        return data


class VirtualTryOnStage(PipelineStage):
    """Compose the garment onto the person (abstract)."""

    stage_key = "virtual_try_on"

    @abc.abstractmethod
    def compose(self, ctx: PipelineContext) -> bytes: ...

    def run(self, ctx: PipelineContext) -> PipelineContext:
        ctx.result_bytes = self.compose(ctx)
        return ctx


class MockVirtualTryOnStage(VirtualTryOnStage):
    """Composite the mock panel over the person's torso. The person image is
    the base of the result, so the face is never altered."""

    def compose(self, ctx: PipelineContext) -> bytes:
        return _mock_tryon_compose(ctx.person_bytes, ctx.garment_bytes, ctx.input_.garment_type)


class HttpVirtualTryOnStage(VirtualTryOnStage):
    """Warp + compose a ready garment onto the person via an external VTON
    service (CatVTON / IDM-VTON endpoint).

    The default contract mirrors the official IDM-VTON FastAPI wrapper
    (``app.py``): ``POST /tryon`` with a ``person`` image file and a
    ``cloth``/``garment`` image file, returns try-on image bytes.

    Requires AI_TRYON_GENERATION_ENDPOINT. Fails honestly otherwise.
    """

    def __init__(self, endpoint: str = "", garment_field: str = "garment"):
        self.endpoint = endpoint or settings.tryon_generation_endpoint
        self.garment_field = garment_field

    def compose(self, ctx: PipelineContext) -> bytes:
        if not self.endpoint:
            raise ProviderConfigurationError(
                "Virtual try-on requires AI_TRYON_GENERATION_ENDPOINT. "
                "Point it at a CatVTON/IDM-VTON service, or use AI_PROVIDER=mock for development."
            )
        if ctx.garment_bytes is None:
            raise TryOnComposeFailed("No garment representation available for try-on.")
        try:
            resp = httpx.post(
                self.endpoint,
                files={
                    "person": ("person.jpg", ctx.person_bytes, "image/jpeg"),
                    self.garment_field: (
                        f"{self.garment_field}.jpg",
                        ctx.garment_bytes,
                        "image/jpeg",
                    ),
                },
                data={
                    "garment_type": ctx.input_.garment_type,
                    "garment_style": ctx.input_.garment_style,
                },
                timeout=300,
            )
            resp.raise_for_status()
            data: bytes = resp.content
        except Exception as exc:
            raise TryOnComposeFailed(f"Try-on service error: {exc}")
        if not data or len(data) < 100:
            raise TryOnComposeFailed("Try-on service returned an empty image.")
        _require_decodable(data, "try-on result")
        return data


class ImageGenGarmentConstructionStage(GarmentConstructionStage):
    """Render the garment from the raw fabric using a real image-gen backend.

    The backend performs a genuine fabric -> garment model call (never a fake
    or overlay). Missing backend config fails honestly with
    ProviderConfigurationError.
    """

    stage_key = "construct_garment"

    def __init__(self, backend: ImageGenBackend):
        if backend is None:
            raise ProviderConfigurationError("No image generation backend configured.")
        self.backend = backend

    def build_garment(self, ctx: PipelineContext) -> bytes:
        analysis = ctx.fabric_analysis.to_dict() if ctx.fabric_analysis else None
        model = getattr(self.backend, "model_tag", "") or getattr(self.backend, "model", "")
        print(
            f"[TRYON][REFERENCE] person_image=missing "
            f"garment_image=present garment_reference_attached=true "
            f"input_image_count=1 model={model}",
            flush=True,
        )
        from .prompts import VastrAIPrompts

        prompt = VastrAIPrompts().build_garment(
            ctx.input_.garment_type, ctx.input_.garment_style, analysis
        )
        print(
            f"[TRYON][FIDELITY] reference_image_used=true "
            f"prompt_contains_garment_preservation="
            f"{str(VastrAIPrompts.PRESERVATION_MARKER in prompt).lower()}",
            flush=True,
        )
        VastrAIPrompts.audit_request(
            "garment",
            ctx.input_.garment_type,
            ctx.input_.garment_style,
            reference_attached=True,
        )
        try:
            data = self.backend.generate_garment(
                ctx.fabric_bytes,
                ctx.input_.garment_type,
                ctx.input_.garment_style,
                analysis,
            )
        except ImageGenNotConfigured as exc:
            raise ProviderConfigurationError(str(exc))
        except ImageGenError as exc:
            raise FabricGenerationFailed(
                f"{self.backend.key} garment generation failed: {exc}"
            ) from exc
        except Exception as exc:
            raise FabricGenerationFailed(
                f"{self.backend.key} garment generation failed: {exc}"
            ) from exc
        if not data or len(data) < 100:
            raise FabricGenerationFailed("Garment generation returned an empty image.")
        _require_decodable(data, "generated garment")
        return data


class ImageGenVirtualTryOnStage(VirtualTryOnStage):
    """Dress the person in the generated garment using a real image-gen backend.

    Sends the person photo + the generated garment as references and asks the
    model to alter the clothing while preserving identity/pose.
    """

    stage_key = "virtual_try_on"

    def __init__(self, backend: ImageGenBackend):
        if backend is None:
            raise ProviderConfigurationError("No image generation backend configured.")
        self.backend = backend

    def compose(self, ctx: PipelineContext) -> bytes:
        if ctx.garment_bytes is None:
            raise TryOnComposeFailed("No garment representation available for try-on.")
        analysis = ctx.fabric_analysis.to_dict() if ctx.fabric_analysis else None
        model = getattr(self.backend, "model_tag", "") or getattr(self.backend, "model", "")
        print(
            f"[TRYON][REFERENCE] person_image=present "
            f"garment_image=present garment_reference_attached=true "
            f"input_image_count=2 model={model}",
            flush=True,
        )
        from .prompts import VastrAIPrompts

        prompt = VastrAIPrompts().build_tryon(
            ctx.input_.garment_type, ctx.input_.garment_style, analysis
        )
        print(
            f"[TRYON][FIDELITY] reference_image_used=true "
            f"prompt_contains_garment_preservation="
            f"{str(VastrAIPrompts.PRESERVATION_MARKER in prompt).lower()}",
            flush=True,
        )
        VastrAIPrompts.audit_request(
            "tryon",
            ctx.input_.garment_type,
            ctx.input_.garment_style,
            reference_attached=True,
        )
        try:
            data = self.backend.generate_tryon(
                ctx.person_bytes,
                ctx.garment_bytes,
                ctx.input_.garment_type,
                ctx.input_.garment_style,
                analysis,
            )
        except ImageGenNotConfigured as exc:
            raise ProviderConfigurationError(str(exc))
        except ImageGenError as exc:
            raise TryOnComposeFailed(
                f"{self.backend.key} try-on failed: {exc}"
            ) from exc
        except Exception as exc:
            raise TryOnComposeFailed(
                f"{self.backend.key} try-on failed: {exc}"
            ) from exc
        if not data or len(data) < 100:
            raise TryOnComposeFailed("Try-on service returned an empty image.")
        _require_decodable(data, "try-on result")
        return data


class GeminiGarmentConstructionStage(ImageGenGarmentConstructionStage):
    """Backward-compatible Gemini stage (Nano Banana garment rendering).

    Uses the fabric swatch as a reference + a descriptive prompt. Fails
    honestly (ProviderConfigurationError) when GEMINI_API_KEY is unset.
    """

    def __init__(self, aspect_ratio: str = "3:4"):
        super().__init__(GeminiImageGenBackend(aspect_ratio=aspect_ratio))


class GeminiVirtualTryOnStage(ImageGenVirtualTryOnStage):
    """Backward-compatible Gemini stage (try-on via image editing)."""

    def __init__(self, aspect_ratio: str = "3:4"):
        super().__init__(GeminiImageGenBackend(aspect_ratio=aspect_ratio))


class IdentityPreservationStage(PipelineStage):
    stage_key = "identity_check"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        score = identity_metrics(ctx.person_bytes, ctx.result_bytes)
        ctx.identity_score = score
        threshold = settings.identity_min_score
        if threshold and score < threshold:
            raise QualityCheckFailed(
                f"Identity preservation check failed (score {score:.2f} < {threshold})."
            )
        return ctx


class QualityValidationStage(PipelineStage):
    stage_key = "quality_check"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        data = ctx.result_bytes
        if not data or len(data) < 500:
            raise QualityCheckFailed("Generated result is empty.")
        from PIL import Image

        try:
            im = Image.open(io.BytesIO(data))
            im.load()
            w, h = im.size
        except Exception:
            raise QualityCheckFailed("Generated result is not a valid image.")
        if min(w, h) < 128:
            raise QualityCheckFailed(f"Generated result is too small ({w}x{h}).")
        buf = io.BytesIO()
        try:
            im.convert("RGB").save(buf, "JPEG", quality=90)
        except Exception:
            raise QualityCheckFailed("Generated result could not be encoded.")
        if len(buf.getvalue()) < 500:
            raise QualityCheckFailed("Generated result is too small to store.")
        return ctx


class UploadResultStage(PipelineStage):
    stage_key = "upload_result"

    def __init__(self, allow_placeholder: bool = False):
        self.allow_placeholder = allow_placeholder

    def run(self, ctx: PipelineContext) -> PipelineContext:
        name = f"result-{uuid.uuid4().hex[:12]}.jpg"
        uploaded = upload_bytes(ctx.result_bytes, name, settings.results_folder)
        if uploaded is not None and uploaded.get("url"):
            ctx.result_url = uploaded["url"]
            return ctx
        if self.allow_placeholder:
            label = f"{ctx.input_.garment_type}-{ctx.input_.garment_style}".replace(" ", "-").replace("_", "-").lower()
            ctx.result_url = f"https://placehold.co/400x520/0D0B1A/C9A96A?text=AI+{label}"
            return ctx
        raise UploadFailed("Could not store the generated image (ImageKit not configured).")


class Pipeline:
    """Ordered stages executed against a single TryOnInput."""

    def __init__(self, stages: List[PipelineStage], provider: str):
        self.stages = stages
        self.provider = provider

    def execute(self, input_: TryOnInput) -> PipelineContext:
        ctx = PipelineContext(input_=input_, provider=self.provider)
        for stage in self.stages:
            try:
                ctx.log(stage.stage_key, "start")
                ctx = stage.run(ctx)
                ctx.log(stage.stage_key, "ok")
            except TryOnError as exc:
                ctx.log(stage.stage_key, "error", str(exc))
                raise
        return ctx