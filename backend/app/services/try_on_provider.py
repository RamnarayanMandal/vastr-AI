"""Virtual Try-On provider abstraction.

The rest of the application depends only on ``VirtualTryOnProvider`` and must
never call a specific model directly.

Known situation:
  1. Ready-made garment: person + garment image -> try-on.
  2. Raw fabric: person + raw fabric + garment type + style -> generated garment.

Case 2 (fabric-to-garment) is the harder generation problem. Real providers
(CatVTON / IDM-VTON) only warp finished garments onto a person, so this package
runs a two-stage pipeline per provider:

  Validate -> Analyze Fabric -> Build Garment -> Virtual Try-On
            -> Identity Check -> Quality Check -> Upload -> Save

The garment-building stage needs a fabric -> garment model endpoint
(``AI_GARMENT_GENERATION_ENDPOINT``) and the try-on stage needs a CatVTON /
IDM-VTON endpoint (``AI_TRYON_GENERATION_ENDPOINT``). If an endpoint is missing
the pipeline fails honestly with a clear message - it never fabricates a result.

``GeminiProvider`` and ``FluxProvider`` instead drive the ENTIRE raw-fabric ->
garment -> person workflow through a single real image-generation backend
(``services.image_gen``): one model call renders the garment from the fabric,
a second edits the person in. ``IDMVTONProvider`` stays experimental.

``MockVirtualTryOnProvider`` is the only provider that runs GPU-free and is
clearly marked as a development/test demo.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Optional

from ..config import settings
from .image_gen import (
    FluxImageGenBackend,
    GeminiImageGenBackend,
    ImageGenBackend,
    OpenAIImageGenBackend,
    OpenRouterImageGenBackend,
)
from .pipeline import (
    AnalyzeFabricStage,
    HttpGarmentConstructionStage,
    HttpVirtualTryOnStage,
    IdentityPreservationStage,
    ImageGenGarmentConstructionStage,
    ImageGenVirtualTryOnStage,
    MockGarmentConstructionStage,
    MockVirtualTryOnStage,
    Pipeline,
    QualityValidationStage,
    TryOnError,
    TryOnInput,
    UploadResultStage,
    ValidateInputsStage,
)

# Errors re-exported so callers import from one place.
from .pipeline import (  # noqa: F401, E402
    FabricGenerationFailed,
    PermanentTryOnError,
    ProviderConfigurationError,
    QualityCheckFailed,
    RetryableTryOnError,
)


@dataclass
class TryOnOutput:
    result_url: Optional[str]  # URL of the generated image
    model_version: str
    provider: str


class VirtualTryOnProvider(abc.ABC):
    """Interface every provider must implement."""

    provider_name: str = "base"
    model_version: str = "base"

    @abc.abstractmethod
    def build_pipeline(self) -> Pipeline:
        """Return the ordered pipeline for this provider."""
        raise NotImplementedError

    @abc.abstractmethod
    def generate(self, input_: TryOnInput) -> TryOnOutput:
        """Run inference and return a result image URL.

        Raises ``TryOnError`` on failure so callers can retry cleanly.
        """
        raise NotImplementedError

    def name(self) -> str:
        return self.provider_name


class MockVirtualTryOnProvider(VirtualTryOnProvider):
    """Deterministic, no-GPU provider for tests and local development.

    Runs the real staged pipeline (validate -> analyze -> construct -> try-on
    -> identity -> quality -> upload) but every time-consuming stage is
    Pillow-based so it works without an AI backend. The result is a clearly
    labelled DEMO PREVIEW composite - the person image stays the base of the
    image and the face is never altered. NOT suitable for real use.
    """

    provider_name = "mock"
    model_version = "mock-pipeline-1.0"

    def build_pipeline(self) -> Pipeline:
        return Pipeline(
            [
                ValidateInputsStage(allow_synthesis=True),
                AnalyzeFabricStage(),
                MockGarmentConstructionStage(),
                MockVirtualTryOnStage(),
                IdentityPreservationStage(),
                QualityValidationStage(),
                UploadResultStage(allow_placeholder=True),
            ],
            provider=self.provider_name,
        )

    def generate(self, input_: TryOnInput) -> TryOnOutput:
        # Simulate inference latency (tunable for tests via attribute).
        import time

        time.sleep(getattr(self, "_delay", 0.4))
        if self._consume_fail():
            raise TryOnError("mock failure injected in provider (dev only).")
        ctx = self.build_pipeline().execute(input_)
        return TryOnOutput(
            result_url=ctx.result_url,
            model_version=self.model_version,
            provider=self.provider_name,
        )

    def fail_next(self):
        """Test helper: make the next generation raise TryOnError."""
        self._should_fail = True

    def _consume_fail(self) -> bool:
        if getattr(self, "_should_fail", False):
            self._should_fail = False
            return True
        return False


class CatVTONProvider(VirtualTryOnProvider):
    """CatVTON-based provider.

    CatVTON warps a ready-made garment onto a person's photo; it does NOT
    synthesize a new garment from raw fabric by itself. VastrAI therefore runs
    the two-stage pipeline:

      1. fabric -> garment representation   (AI_GARMENT_GENERATION_ENDPOINT)
      2. person + garment -> try-on         (AI_TRYON_GENERATION_ENDPOINT, CatVTON)

    If an endpoint is missing the pipeline fails honestly (ProviderConfigurationError)
    with a message telling the operator what to configure.
    """

    provider_name = "catvton"
    model_version = "catvton-pipeline-1.0"

    def build_pipeline(self) -> Pipeline:
        return Pipeline(
            [
                ValidateInputsStage(),
                AnalyzeFabricStage(),
                HttpGarmentConstructionStage(),
                HttpVirtualTryOnStage(),
                IdentityPreservationStage(),
                QualityValidationStage(),
                UploadResultStage(),
            ],
            provider=self.provider_name,
        )

    def generate(self, input_: TryOnInput) -> TryOnOutput:
        ctx = self.build_pipeline().execute(input_)
        return TryOnOutput(
            result_url=ctx.result_url,
            model_version=self.model_version,
            provider=self.provider_name,
        )


class IDMVTONProvider(VirtualTryOnProvider):
    """IDM-VTON-based provider (same two-stage contract as CatVTON)."""

    provider_name = "idmvton"
    model_version = "idmvton-pipeline-1.0"

    def build_pipeline(self) -> Pipeline:
        return Pipeline(
            [
                ValidateInputsStage(),
                AnalyzeFabricStage(),
                HttpGarmentConstructionStage(),
                HttpVirtualTryOnStage(garment_field="cloth"),
                IdentityPreservationStage(),
                QualityValidationStage(),
                UploadResultStage(),
            ],
            provider=self.provider_name,
        )

    def generate(self, input_: TryOnInput) -> TryOnOutput:
        ctx = self.build_pipeline().execute(input_)
        return TryOnOutput(
            result_url=ctx.result_url,
            model_version=self.model_version,
            provider=self.provider_name,
        )


class GeminiProvider(VirtualTryOnProvider):
    """Gemini / Nano Banana image-generation provider (real AI, no fake data).

    Runs the full raw-fabric -> garment -> person workflow through the generic
    image-generation backend abstraction:

      1. Raw fabric -> rendered garment (fabric swatch as reference)
      2. Person + garment -> try-on     (both images as references)

    Requires ``GEMINI_API_KEY``. Without it the pipeline fails honestly with
    ``ProviderConfigurationError`` - it never fabricates a result.
    """

    provider_name = "gemini"
    model_version = "gemini-3.1-flash-image-1.0"

    def __init__(self, backend: Optional[ImageGenBackend] = None):
        self.backend = backend or GeminiImageGenBackend()

    def build_pipeline(self) -> Pipeline:
        return Pipeline(
            [
                ValidateInputsStage(),
                AnalyzeFabricStage(),
                ImageGenGarmentConstructionStage(self.backend),
                ImageGenVirtualTryOnStage(self.backend),
                IdentityPreservationStage(),
                QualityValidationStage(),
                UploadResultStage(),
            ],
            provider=self.provider_name,
        )

    def generate(self, input_: TryOnInput) -> TryOnOutput:
        ctx = self.build_pipeline().execute(input_)
        return TryOnOutput(
            result_url=ctx.result_url,
            model_version=self.model_version,
            provider=self.provider_name,
        )


class FluxProvider(VirtualTryOnProvider):
    """FLUX image-generation provider (real AI, no fake data).

    Identical two-stage workflow to ``GeminiProvider`` but driven through a
    FLUX-compatible image API (``FLUX_ENDPOINT`` + optional ``FLUX_API_KEY``).

    Experimental alternative provider: when the endpoint is unset it fails
    honestly with ``ProviderConfigurationError`` - it never fabricates a result.
    """

    provider_name = "flux"
    model_version = "flux-pipeline-1.0"

    def __init__(self, backend: Optional[ImageGenBackend] = None):
        self.backend = backend or FluxImageGenBackend()

    def build_pipeline(self) -> Pipeline:
        return Pipeline(
            [
                ValidateInputsStage(),
                AnalyzeFabricStage(),
                ImageGenGarmentConstructionStage(self.backend),
                ImageGenVirtualTryOnStage(self.backend),
                IdentityPreservationStage(),
                QualityValidationStage(),
                UploadResultStage(),
            ],
            provider=self.provider_name,
        )

    def generate(self, input_: TryOnInput) -> TryOnOutput:
        ctx = self.build_pipeline().execute(input_)
        return TryOnOutput(
            result_url=ctx.result_url,
            model_version=self.model_version,
            provider=self.provider_name,
        )


class OpenAIProvider(VirtualTryOnProvider):
    """OpenAI image-generation provider (real AI, no fake data).

    Identical two-stage workflow to ``GeminiProvider`` but driven through the
    OpenAI Images API (``gpt-image-2``) reference-image editing.

    Requires ``OPENAI_API_KEY``. Without it the pipeline fails honestly with
    ``ProviderConfigurationError`` - it never fabricates a result.
    """

    provider_name = "openai"
    model_version = "openai-gpt-image-2"

    def __init__(self, backend: Optional[ImageGenBackend] = None):
        self.backend = backend or OpenAIImageGenBackend()

    def build_pipeline(self) -> Pipeline:
        return Pipeline(
            [
                ValidateInputsStage(),
                AnalyzeFabricStage(),
                ImageGenGarmentConstructionStage(self.backend),
                ImageGenVirtualTryOnStage(self.backend),
                IdentityPreservationStage(),
                QualityValidationStage(),
                UploadResultStage(),
            ],
            provider=self.provider_name,
        )

    def generate(self, input_: TryOnInput) -> TryOnOutput:
        ctx = self.build_pipeline().execute(input_)
        return TryOnOutput(
            result_url=ctx.result_url,
            model_version=self.model_version,
            provider=self.provider_name,
        )


class OpenRouterProvider(VirtualTryOnProvider):
    """OpenRouter image-generation provider (real AI, no fake data).

    Identical two-stage workflow to ``OpenAIProvider`` but driven through the
    OpenRouter dedicated Image API with ``meta/muse-image`` (or any image model
    slug from ``OPENROUTER_MODEL``).

    Requires ``OPENROUTER_API_KEY``. Without it the pipeline fails honestly
    with ``ProviderConfigurationError`` - it never fabricates a result.
    """

    provider_name = "openrouter"
    model_version = "openrouter-image-1.0"

    def __init__(self, backend: Optional[ImageGenBackend] = None):
        self.backend = backend or OpenRouterImageGenBackend()

    def build_pipeline(self) -> Pipeline:
        return Pipeline(
            [
                ValidateInputsStage(),
                AnalyzeFabricStage(),
                ImageGenGarmentConstructionStage(self.backend),
                ImageGenVirtualTryOnStage(self.backend),
                IdentityPreservationStage(),
                QualityValidationStage(),
                UploadResultStage(),
            ],
            provider=self.provider_name,
        )

    def generate(self, input_: TryOnInput) -> TryOnOutput:
        ctx = self.build_pipeline().execute(input_)
        return TryOnOutput(
            result_url=ctx.result_url,
            model_version=self.model_version,
            provider=self.provider_name,
        )


def get_provider(name: Optional[str] = None) -> VirtualTryOnProvider:
    """Factory. 'name' defaults to the configured provider.

    ``settings.ai_provider`` (env ``AI_PROVIDER``) wins over the legacy
    ``try_on_provider`` (env ``TRY_ON_PROVIDER``). Any value missing from the
    registry falls back to the mock (development) provider.
    """
    chosen = (
        name
        or settings.ai_provider
        or settings.try_on_provider
        or "mock"
    )
    providers: dict = {
        "mock": MockVirtualTryOnProvider,
        "catvton": CatVTONProvider,
        "idmvton": IDMVTONProvider,
        "gemini": GeminiProvider,
        "flux": FluxProvider,
        "openai": OpenAIProvider,
        "openrouter": OpenRouterProvider,
    }
    cls = providers.get(chosen, MockVirtualTryOnProvider)
    return cls()