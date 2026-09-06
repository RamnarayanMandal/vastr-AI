from unittest.mock import patch

import pytest

from app.services.pipeline import (
    ProviderConfigurationError,
    synthesize_fabric_bytes,
    synthesize_person_bytes,
)
from app.services.try_on_provider import (
    CatVTONProvider,
    GeminiProvider,
    IDMVTONProvider,
    MockVirtualTryOnProvider,
    TryOnInput,
    TryOnError,
    get_provider,
)


def test_mock_provider_generates():
    provider = MockVirtualTryOnProvider()
    provider._delay = 0
    inp = TryOnInput(
        person_image_url="https://example.com/person.jpg",
        fabric_image_url="https://example.com/fabric.jpg",
        garment_type="shirt",
        garment_style="casual",
    )
    output = provider.generate(inp)
    assert output.result_url is not None
    assert output.provider == "mock"


def test_mock_provider_output_format():
    provider = MockVirtualTryOnProvider()
    provider._delay = 0
    inp = TryOnInput(
        person_image_url="https://example.com/p.jpg",
        fabric_image_url="https://example.com/f.jpg",
        garment_type="top",
        garment_style="boho",
        gender="WOMEN",
    )
    output = provider.generate(inp)
    assert output.model_version == "mock-pipeline-1.0"
    assert output.provider == "mock"
    assert isinstance(output.result_url, str)


def test_mock_provider_output_is_demo_stamped():
    provider = MockVirtualTryOnProvider()
    provider._delay = 0
    inp = TryOnInput(
        person_image_url="https://example.com/p.jpg",
        fabric_image_url="https://example.com/f.jpg",
        garment_type="shirt",
        garment_style="casual",
    )
    with patch(
        "app.services.pipeline.download_url",
        side_effect=lambda url: synthesize_fabric_bytes(),
    ):
        output = provider.generate(inp)
        ctx = provider.build_pipeline().execute(inp)
    # No ImageKit in tests -> demo placeholder URL is returned.
    assert output.result_url.startswith("https://placehold.co")
    # Person image stays the base of the composite -> identity is preserved.
    assert ctx.identity_score is not None and ctx.identity_score > 0.9


def test_get_provider_factory():
    mock_p = get_provider("mock")
    assert isinstance(mock_p, MockVirtualTryOnProvider)

    cat_p = get_provider("catvton")
    assert isinstance(cat_p, CatVTONProvider)

    idm_p = get_provider("idmvton")
    assert isinstance(idm_p, IDMVTONProvider)

    gem_p = get_provider("gemini")
    assert isinstance(gem_p, GeminiProvider)

    default_p = get_provider(None)
    assert isinstance(default_p, MockVirtualTryOnProvider)

    unknown_p = get_provider("nonexistent")
    assert isinstance(unknown_p, MockVirtualTryOnProvider)


def test_catvton_raises():
    provider = CatVTONProvider()
    inp = TryOnInput(
        person_image_url="https://example.com/p.jpg",
        fabric_image_url="https://example.com/f.jpg",
        garment_type="shirt",
        garment_style="casual",
    )
    with pytest.raises(TryOnError):
        provider.generate(inp)


def test_catvton_fails_honestly_when_unconfigured():
    """With real images available but no model endpoints, the pipeline must
    raise a permanent, informative error - never a fabricated result."""
    provider = CatVTONProvider()
    inp = TryOnInput(
        person_image_url="https://example.com/p.jpg",
        fabric_image_url="https://example.com/f.jpg",
        garment_type="shirt",
        garment_style="casual",
    )
    with patch(
        "app.services.pipeline.download_url",
        side_effect=[synthesize_person_bytes(), synthesize_fabric_bytes()],
    ):
        with pytest.raises(ProviderConfigurationError) as exc_info:
            provider.generate(inp)
    assert "AI_GARMENT_GENERATION_ENDPOINT" in str(exc_info.value)


def test_idmvton_raises():
    provider = IDMVTONProvider()
    inp = TryOnInput(
        person_image_url="https://example.com/p.jpg",
        fabric_image_url="https://example.com/f.jpg",
        garment_type="shirt",
        garment_style="casual",
    )
    with pytest.raises(TryOnError):
        provider.generate(inp)


def test_gemini_fails_honestly_when_unconfigured():
    """Without GEMINI_API_KEY the pipeline must raise a permanent,
    informative error - never a fabricated result."""
    provider = GeminiProvider()
    inp = TryOnInput(
        person_image_url="https://example.com/p.jpg",
        fabric_image_url="https://example.com/f.jpg",
        garment_type="shirt",
        garment_style="casual",
    )
    with patch(
        "app.services.pipeline.download_url",
        side_effect=[synthesize_person_bytes(), synthesize_fabric_bytes()],
    ):
        with pytest.raises(ProviderConfigurationError) as exc_info:
            provider.generate(inp)
    assert "GEMINI_API_KEY" in str(exc_info.value)


def test_gemini_generates_with_mock_api():
    """With GEMINI_API_KEY set and the API patched to return a valid image,
    the full Gemini pipeline returns a result - no faked data."""
    provider = GeminiProvider()
    inp = TryOnInput(
        person_image_url="https://example.com/p.jpg",
        fabric_image_url="https://example.com/f.jpg",
        garment_type="shirt",
        garment_style="casual",
    )
    with patch(
        "app.services.pipeline.download_url",
        side_effect=[synthesize_person_bytes(), synthesize_fabric_bytes()],
    ), patch(
        "app.services.pipeline.upload_bytes",
        return_value={"url": "https://ik.imagekit.io/vastrai/result.jpg"},
    ), patch(
        "app.services.pipeline.settings.gemini_api_key",
        "test-key",
    ), patch(
        "app.services.gemini.generate_image",
        return_value=synthesize_fabric_bytes(),
    ):
        output = provider.generate(inp)
    assert output.provider == "gemini"
    assert output.model_version == "gemini-3.1-flash-image-1.0"
    assert output.result_url == "https://ik.imagekit.io/vastrai/result.jpg"
