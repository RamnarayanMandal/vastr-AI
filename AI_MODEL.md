# VastrAI AI Model

The AI layer is split into two cooperating pieces, both behind stable interfaces:

1. **`Pipeline`** (`backend/app/services/pipeline.py`) - an ordered, stage-based execution engine. Each provider composes its own list of stages.
2. **`VirtualTryOnProvider`** (`backend/app/services/try_on_provider.py`) - the abstraction everything above it (API router, Celery worker, DB model, mobile app) depends on. It re-exports the pipeline types so callers import from one place.

This lets a model be swapped or added without touching the rest of the system.

## The Provider Abstraction

```python
@dataclass
class TryOnInput:
    person_image_url: str    # customer photo
    fabric_image_url: str    # cloth / fabric / ready-made garment
    garment_type: str        # e.g. "shirt", "saree", "kurta"
    garment_style: str       # e.g. "slim", "traditional"
    gender: Optional[str]    # "MEN" | "WOMEN" | "KIDS"

@dataclass
class TryOnOutput:
    result_url: Optional[str]   # URL of the generated image
    model_version: str          # recorded on the job, e.g. "mock-pipeline-1.0"
    provider: str               # provider_name, e.g. "mock"

class VirtualTryOnProvider(abc.ABC):
    provider_name: str = "base"
    model_version: str = "base"

    @abc.abstractmethod
    def build_pipeline(self) -> Pipeline: ...   # stages for this provider
    @abc.abstractmethod
    def generate(self, input_: TryOnInput) -> TryOnOutput: ...
```

Contract notes:

- `generate()` runs `build_pipeline().execute(input_)`, which returns a `PipelineContext` carrying the staged outputs (fabric analysis, identity score, result URL). The worker stores the result URL on `try_on_results`.
- Providers must raise `TryOnError` subclasses. The Celery worker retries **retryable** errors and fails the job **permanently** on `PermanentTryOnError`.
- Providers are resolved through `get_provider(name)` and selected via `AI_PROVIDER` (fallback `TRY_ON_PROVIDER`).

## The Staged Pipeline

Every provider composes the same seven stages; only the garment-construction and virtual-try-on stages differ by provider.

| Stage | Purpose |
|-------|---------|
| `Validate Inputs` | Download + decode person & fabric images; validate garment type/style/gender. May synthesize sample images for the mock provider. |
| `Analyze Fabric` | Pillow-based analysis: dominant color, palette, pattern detection, brightness -> a `FabricAnalysis` used to drive generation. |
| `Generate Garment Representation` | Build a garment from the raw fabric (see the two input situations below). |
| `Virtual Try-On` | Compose the garment onto the person photo. |
| `Identity Preservation` | Structural overlap score of the face region between the source photo and the result (0-1). Gated by `identity_min_score`. |
| `Quality Validation` | Decodes the result, checks min dimensions and re-encodability. |
| `Upload Result` | Uploads to ImageKit and records the public URL. |

`Pipeline.execute()` returns a `PipelineContext` recording a `stage_log` and intermediate artifacts (`person_bytes`, `fabric_analysis`, `garment_bytes`, `result_bytes`, `identity_score`, `result_url`).

## The Two Input Situations

1. **Ready-made garment** - customer photo + photo of an actual finished garment. The classic virtual try-on problem (person + garment -> person wearing it). CatVTON and IDM-VTON are built for this.
2. **Raw fabric-to-garment** - customer photo + photo of **raw fabric** (a bolt of cloth) + garment type/style. The system must first synthesize the garment from the fabric, then fit it onto the person. This is the harder generation problem and **cannot be faked with a texture overlay**.

VastrAI separates these into the `Generate Garment Representation` stage (needs a fabric -> garment model) and the `Virtual Try-On` stage (needs a CatVTON / IDM-VTON endpoint). This is the primary product use case for fabric/clothing shops.

## Errors

All pipeline errors live in `pipeline.py` and are re-exported by `try_on_provider.py`:

- `TryOnError` (base) with a `retryable` attribute.
- `RetryableTryOnError` - transient (model timeout, upload hiccup); the worker retries with exponential backoff.
- `PermanentTryOnError` - permanent (bad input, missing config); the worker fails the job immediately.
- Subclasses: `InputValidationError`, `ProviderConfigurationError`, `FabricGenerationFailed`, `TryOnComposeFailed`, `QualityCheckFailed`, `UploadFailed`.

**Honest failures**: if a real provider is missing an endpoint (e.g. `AI_GARMENT_GENERATION_ENDPOINT`), it raises `ProviderConfigurationError` with a clear message telling the operator what to configure. It never fabricates a result.

## MockVirtualTryOnProvider

`provider_name = "mock"`, `model_version = "mock-pipeline-1.0"` - default in dev/tests.

- Runs the **real staged pipeline** (`Validate -> Analyze -> Construct -> Try-On -> Identity -> Quality -> Upload`), but each time-consuming stage is Pillow-based so it runs GPU-free.
- Uses `ImageKit.upload_bytes`; falls back to a `placehold.co` placeholder URL when ImageKit is not configured.
- The composite keeps the **person image as its base** and never alters the face - the demo composite carries a `DEMO PREVIEW` stamp and the face-region identity score stays high.
- Exposes `fail_next()` as a test helper.

**Not suitable for real use.** It exists so the app, API, and worker can be developed, tested, and demoed without an AI backend.

## CatVTONProvider

`provider_name = "catvton"`, `model_version = "catvton-pipeline-1.0"`.

- Pipeline: `Validate -> Analyze -> HttpGarmentConstruction -> HttpVirtualTryOn -> Identity -> Quality -> Upload`.
- `HttpVirtualTryOnStage` POSTs the person + garment to `AI_TRYON_GENERATION_ENDPOINT` (CatVTON service).
- `HttpGarmentConstructionStage` POSTs the fabric to `AI_GARMENT_GENERATION_ENDPOINT` (a fabric -> garment model) to produce the garment representation that CatVTON then warps.

If either endpoint is empty, it raises `ProviderConfigurationError` - CatVTON alone cannot synthesize a garment from raw fabric.

## IDMVTONProvider

Same contract as CatVTON with `provider_name = "idmvton"`, `model_version = "idmvton-pipeline-1.0"`.

## GeminiProvider

`provider_name = "gemini"`, `model_version = "gemini-3.1-flash-image-1.0"` - **real AI image generation, no fake data**.

The Gemini provider drives the whole fabric -> garment -> try-on journey with Google's Gemini image model ("Nano Banana", e.g. `gemini-3.1-flash-image`) via its native `generateContent` REST endpoint (`backend/app/services/gemini.py`). It runs through the generic `ImageGenBackend` seam (see below):

1. **Construct garment** (`ImageGenGarmentConstructionStage` via `GeminiImageGenBackend`) - sends the raw fabric swatch as an inline reference image plus a prompt describing the garment type/style, and asks the model to render a flat garment in that exact fabric. Returns image bytes.
2. **Virtual try-on** (`ImageGenVirtualTryOnStage`) - sends the customer photo + the generated garment as two inline references plus an edit prompt (dress the person in this garment, keep face/pose/skin tone identical). Returns the try-on image.

Both prompts are seeded from the Pillow fabric analysis (`garment_prompts()` builds the descriptive text from dominant color / pattern / brightness).

Gateway details:

- Endpoint: `POST {gemini_base_url}/models/{gemini_model}:generateContent` with header `x-goog-api-key: $GEMINI_API_KEY`.
- Inline images are base64-encoded with a JPEG/PNG MIME sniff (`_mime_type`).
- Response is parsed for `candidates[].content.parts[].inlineData.data` (base64 image). A response with no image part raises `GeminiAPIError`.

**Honest failures**: without `GEMINI_API_KEY`, the pipeline raises `ProviderConfigurationError` ("requires GEMINI_API_KEY") - it never fabricates output. Transient API failures surface as `FabricGenerationFailed` / `TryOnComposeFailed` (both retryable). Gemini is an image *editor/generator*, so the `IdentityPreservationStage` (structural overlap in the face region) still guards the result with `IDENTITY_MIN_SCORE`.

## The Image-Generation Backend Abstraction

`backend/app/services/image_gen.py` is the shared seam for the whole raw-fabric -> garment -> person workflow. The workflow is exactly two model calls:

1. `generate_garment(fabric, garment_type, garment_style, analysis)` - fabric swatch -> rendered garment.
2. `generate_tryon(person, garment, garment_type, garment_style, analysis)` - person + garment -> try-on.

`ImageGenBackend` is the abstract base; `ImageGenError` / `ImageGenNotConfigured` / `ImageGenAPIError` are the error types. The generic pipeline stages (`ImageGenGarmentConstructionStage`, `ImageGenVirtualTryOnStage`) map `ImageGenNotConfigured` -> `ProviderConfigurationError` (honest failure) and API errors -> the retryable `FabricGenerationFailed` / `TryOnComposeFailed`. Backends never fake or overlay the fabric - they call a model.

### GeminiImageGenBackend

`key = "gemini"` - delegates to `services/gemini.py` (`generate_image` / `garment_prompts`).

### FluxImageGenBackend

`key = "flux"`, `model_tag = <FLUX_MODEL>` (default `flux-dev`) - POSTs JSON to a FLUX-compatible image API:

```
POST {FLUX_ENDPOINT}
{
  "task": "garment" | "tryon",
  "model": "<FLUX_MODEL>",
  "prompt": "...",
  "reference_images": ["<base64 image>", ...]
}
200 -> {"image": "<base64 output>"}   (raw image bytes also accepted)
```

Optional `FLUX_API_KEY` is sent as `Authorization: Bearer <key>`. Without `FLUX_ENDPOINT` it fails honestly with `ImageGenNotConfigured`. This is the install point for a self-hosted FLUX.1-style service; any added endpoint must implement the contract above.

### OpenAIImageGenBackend

`key = "openai"`, `model_tag = <OPENAI_MODEL>` (default `gpt-image-1`) - POSTs `multipart/form-data` to the OpenAI Images API edit endpoint (reference-image editing):

```
POST {OPENAI_BASE_URL}/images/edits          (Authorization: Bearer <key>)
form fields:
  model=gpt-image-1
  prompt=...
  size=1024x1536            # 3:4 aspect (1:1 -> 1024x1024, 4:3 -> 1536x1024)
  quality=high
  output_format=png
  input_fidelity=high       # preserve facial features
  file part "image[]": <image>     (filename + content_type image/png required)
200 -> {"data": [{"b64_json": "<base64 output>"}]}
```

The `image[]` part carries the fabric (garment stage) or person + garment (try-on stage), so `gpt-image-1` edits the customer photo directly - the same reference-image workflow as Gemini. gpt-image models always return `b64_json` (do not send `response_format`). Without `OPENAI_API_KEY` it fails honestly with `ImageGenNotConfigured`. The account/org must have access to the image model (403 otherwise).

## OpenAIProvider

`provider_name = "openai"`, `model_version = "openai-gpt-image-1"` - the full raw-fabric -> garment -> person workflow driven through `OpenAIImageGenBackend`. Select with `AI_PROVIDER=openai`.

## FluxProvider

`provider_name = "flux"`, `model_version = "flux-pipeline-1.0"` - same two-stage workflow as `GeminiProvider` but driven through `FluxImageGenBackend`. Experimental alternative provider; keep `idmvton` if you prefer the CatVTON/IDM-VTON route.

## How to Add a New Provider

1. **Subclass** `VirtualTryOnProvider` in `try_on_provider.py`, set `provider_name`/`model_version`, implement `build_pipeline()` returning a `Pipeline` of stages (reuse `ValidateInputsStage`, `AnalyzeFabricStage`, `IdentityPreservationStage`, `QualityValidationStage`, `UploadResultStage`; provide model-specific construction/try-on stages).
2. For a raw-fabric-capable model, subclass `ImageGenBackend` instead and reuse `ImageGenGarmentConstructionStage` / `ImageGenVirtualTryOnStage` with your backend.
3. **Register it** in the `get_provider` factory's `providers` dict.
4. **Select it** via `AI_PROVIDER=<name>` in `.env` (or `try_on_provider`).
5. **Verify the two input paths** (ready-made garment and raw fabric-to-garment) and add tests in `backend/tests/test_provider.py`.

## Configuration

| Setting | Env | Default |
|---------|-----|---------|
| `ai_provider` | `AI_PROVIDER` | `mock` |
| `image_gen_backend` | `IMAGE_GEN_BACKEND` | `` (defaults to `AI_PROVIDER`) |
| `gemini_api_key` | `GEMINI_API_KEY` | `` (empty = honest failure) |
| `gemini_model` | `GEMINI_MODEL` | `gemini-3.1-flash-image` |
| `gemini_base_url` | `GEMINI_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta` |
| `gemini_timeout` | `GEMINI_TIMEOUT` | `180` |
| `flux_endpoint` | `FLUX_ENDPOINT` | `` (empty = honest failure) |
| `flux_api_key` | `FLUX_API_KEY` | `` |
| `flux_model` | `FLUX_MODEL` | `flux-dev` |
| `flux_timeout` | `FLUX_TIMEOUT` | `300` |
| `openai_api_key` | `OPENAI_API_KEY` | `` (empty = honest failure) |
| `openai_model` | `OPENAI_MODEL` | `gpt-image-1` |
| `openai_base_url` | `OPENAI_BASE_URL` | `https://api.openai.com/v1` |
| `openai_timeout` | `OPENAI_TIMEOUT` | `300` |
| `garment_generation_endpoint` | `AI_GARMENT_GENERATION_ENDPOINT` | `` (empty = honest failure) |
| `tryon_generation_endpoint` | `AI_TRYON_GENERATION_ENDPOINT` | `` (empty = honest failure) |
| `identity_min_score` | `IDENTITY_MIN_SCORE` | `0.0` (0 disables the gate) |
| `try_on_max_retries` | `TRY_ON_MAX_RETRIES` | `4` |
| `retry_backoff_base` | `RETRY_BACKOFF_BASE` | `5` |
| `retry_max_delay` | `RETRY_MAX_DELAY` | `60` |

## Operational Notes

- Inference happens only in the Celery worker (`app/worker/tasks.py`), so the API stays responsive.
- The worker records `provider` and `model_version` on the job row, so every result is traceable.
- Retries use **claim-based idempotency** (an atomic `UPDATE ... WHERE status='QUEUED'`) plus **exponential backoff** (`min(60, 5 * 2**retries)`). The task resets a job to `QUEUED` before `self.retry` so a redelivered run can reclaim it, and duplicates are avoided even if a task is delivered more than once.
