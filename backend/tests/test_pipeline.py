import io

import pytest
from PIL import Image

from app.services.pipeline import (
    AnalyzeFabricStage,
    InputValidationError,
    MockGarmentConstructionStage,
    MockVirtualTryOnStage,
    Pipeline,
    PipelineContext,
    QualityCheckFailed,
    QualityValidationStage,
    TryOnError,
    TryOnInput,
    UploadResultStage,
    ValidateInputsStage,
    _mock_garment_panel,
    _mock_tryon_compose,
    analyze_fabric,
    identity_metrics,
    synthesize_fabric_bytes,
    synthesize_person_bytes,
)


def _ctx(**kw) -> PipelineContext:
    inp = TryOnInput(
        person_image_url="https://example.com/p.jpg",
        fabric_image_url="https://example.com/f.jpg",
        garment_type="shirt",
        garment_style="casual",
        **kw,
    )
    return PipelineContext(input_=inp, provider="mock")


def test_validate_downloads_fail_without_synthesis(monkeypatch):
    from app.services import pipeline

    monkeypatch.setattr(pipeline, "download_url", lambda url: None)
    stage = ValidateInputsStage()
    with pytest.raises(InputValidationError):
        stage.run(_ctx())


def test_validate_synthesizes_when_allowed(monkeypatch):
    from app.services import pipeline

    monkeypatch.setattr(pipeline, "download_url", lambda url: None)
    stage = ValidateInputsStage(allow_synthesis=True)
    ctx = stage.run(_ctx())
    assert ctx.person_bytes is not None
    assert ctx.fabric_bytes is not None


def test_validate_rejects_bad_gender():
    stage = ValidateInputsStage()
    with pytest.raises(InputValidationError):
        stage.run(_ctx(gender="alien"))


def test_validate_rejects_non_image(monkeypatch):
    from app.services import pipeline

    monkeypatch.setattr(pipeline, "download_url", lambda url: b"not an image")
    with pytest.raises(InputValidationError):
        ValidateInputsStage().run(_ctx())


def test_analyze_fabric_solid():
    analysis = analyze_fabric(synthesize_fabric_bytes(color=(58, 131, 200)))
    assert analysis.has_pattern is False
    assert analysis.dominant_hex == "#3a83c8"
    assert 0.3 < analysis.brightness < 0.7


def test_analyze_fabric_patterned():
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (64, 64), (255, 255, 255))
    d = ImageDraw.Draw(img)
    for y in range(0, 64, 4):
        for x in range(0, 64, 4):
            if (x + y) % 8 == 0:
                d.rectangle([x, y, x + 3, y + 3], fill=(10, 10, 10))
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    analysis = analyze_fabric(buf.getvalue())
    assert analysis.has_pattern is True


def test_mock_garment_panel_is_decodable():
    panel = _mock_garment_panel(
        synthesize_fabric_bytes(), analyze_fabric(synthesize_fabric_bytes()), "shirt"
    )
    with Image.open(io.BytesIO(panel)) as im:
        im.verify()


def test_mock_tryon_keeps_face_identity():
    person = synthesize_person_bytes()
    panel = _mock_garment_panel(
        synthesize_fabric_bytes(), analyze_fabric(synthesize_fabric_bytes()), "shirt"
    )
    result = _mock_tryon_compose(person, panel, "shirt")
    score = identity_metrics(person, result)
    assert score > 0.9


def test_identity_metrics_perfect_match():
    person = synthesize_person_bytes()
    assert identity_metrics(person, person) > 0.99


def test_identity_metrics_different_images_low():
    assert identity_metrics(synthesize_person_bytes(), synthesize_fabric_bytes()) < 0.9


def test_mock_generation_stage_chain():
    stage = MockGarmentConstructionStage()
    ctx = _ctx()
    ctx.person_bytes = synthesize_person_bytes()
    ctx.fabric_bytes = synthesize_fabric_bytes()
    ctx.fabric_analysis = analyze_fabric(ctx.fabric_bytes)
    ctx = stage.run(ctx)
    assert ctx.garment_bytes is not None
    ctx = MockVirtualTryOnStage().run(ctx)
    assert ctx.result_bytes is not None


def test_quality_validation_rejects_tiny_image():
    img = Image.new("RGB", (16, 16), (100, 100, 100))
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    ctx = _ctx()
    ctx.result_bytes = buf.getvalue()
    with pytest.raises(QualityCheckFailed):
        QualityValidationStage().run(ctx)


def test_quality_validation_accepts_real_generated():
    ctx = _ctx()
    ctx.result_bytes = _mock_tryon_compose(
        synthesize_person_bytes(),
        _mock_garment_panel(
            synthesize_fabric_bytes(), analyze_fabric(synthesize_fabric_bytes()), "shirt"
        ),
        "shirt",
    )
    QualityValidationStage().run(ctx)


def test_full_mock_pipeline_executes(monkeypatch):
    from app.services import pipeline

    monkeypatch.setattr(pipeline, "download_url", lambda url: None)
    stages = [
        ValidateInputsStage(allow_synthesis=True),
        AnalyzeFabricStage(),
        MockGarmentConstructionStage(),
        MockVirtualTryOnStage(),
        QualityValidationStage(),
        UploadResultStage(allow_placeholder=True),
    ]
    result = Pipeline(stages, provider="mock").execute(_ctx().input_)
    assert result.result_url is not None
    assert result.result_url.startswith("https://placehold.co")
    assert result.stage_log[-1]["stage"] == "upload_result"


def test_pipeline_propagates_input_error(monkeypatch):
    from app.services import pipeline

    monkeypatch.setattr(pipeline, "download_url", lambda url: b"junk")
    stages = [ValidateInputsStage(), AnalyzeFabricStage()]
    with pytest.raises(TryOnError):
        Pipeline(stages, provider="mock").execute(_ctx().input_)


def test_upload_stage_raises_when_not_configured(monkeypatch):
    from app.services import pipeline

    monkeypatch.setattr(pipeline, "upload_bytes", lambda *a, **k: None)
    ctx = _ctx()
    ctx.result_bytes = synthesize_person_bytes()
    with pytest.raises(TryOnError):
        UploadResultStage(allow_placeholder=False).run(ctx)