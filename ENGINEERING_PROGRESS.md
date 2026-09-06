# VastrAI Engineering Progress

Status of the MVP checklist, current implementation state, known limitations, and next steps. Last updated with the initial documentation pass.

## Completed Items

### Mobile (Expo SDK 54 / expo-router)

- Splash screen with brand animation and the "See It. Try It. Wear It." tagline (`app/index.tsx`).
- Register / login flow wired to the backend JWT auth (`app/login.tsx`, `app/register.tsx`, `AuthContext`).
- Tab shell: Home, History, Profile with a floating Try On action (`BottomNav`).
- Try-on wizard: gender -> garment -> style -> upload (`tryon/index`, `tryon/garment`, `tryon/style`, `tryon/upload`), backed by `src/constants/garments.ts` (genders, per-gender garment catalogs, per-garment styles).
- In-app camera capture for person and fabric with framing guides (`expo-camera`, `app/camera/*`), plus gallery import (`expo-image-picker`).
- Image uploads streamed to the API through `TryOnContext` (`uploadPerson`, `uploadFabric`) with per-step upload states.
- Review screen with completeness checklist and warnings (`app/review.tsx`).
- Processing screen with staged progress animation and job polling (`app/processing/[jobId].tsx`).
- Error handling screen with retry / change-image actions (`app/processing-error/[jobId].tsx`).
- Result screen with draggable before/after comparison slider, share (React Native `Share`), and garment metadata (`app/result/[jobId].tsx`).
- Local history persisted in AsyncStorage (`storage.ts`), rendered in the History tab.
- Full try-on draft state persisted across app restarts (`TryOnDraft`, statuses IDLE -> ... -> COMPLETED/FAILED).
- TypeScript strict typecheck (`npm run typecheck`).

### Backend (FastAPI / SQLAlchemy / Celery)

- FastAPI app with `GET /health`, CORS, and `/api/v1` router prefix (`app/main.py`).
- Env-driven settings (`config.py`) and a copy-ready `.env.example`.
- JWT auth: register, login-by-email-or-mobile, `GET /auth/me`; bearer-token dependency (`security.py`, `deps.py`, `router/auth.py`).
- Image upload endpoints for person and fabric with content-type and 15 MB size validation; ImageKit integration with a placeholder-URL fallback when credentials are absent (`router/uploads.py`, `services/imagekit.py`).
- Try-on job creation (`202`, one `TryOnJob` row) with ownership checks on both images (`router/try_on.py`).
- Job polling endpoints: `GET /try-on/{id}` and `GET /try-on/{id}/result` (404 until `COMPLETED`).
- Celery worker executing jobs end to end: `QUEUED -> PROCESSING -> COMPLETED/FAILED`, with retries on `TryOnError` and result persistence (`worker/tasks.py`, `worker/celery_app.py`).
- Complete data model: `users`, `media_assets` (person/fabric/result), `try_on_jobs`, `try_on_results` (`models.py`).
- Alembic migration `001_initial` creating all four tables with indexes and FKs.
- `docker-compose.yml` and Dockerfiles for `api` and `worker` (Postgres 16 + Redis 7).

### AI Abstraction

- Stage-based `Pipeline` engine with `PipelineContext` and seven stages (`services/pipeline.py`): Validate Inputs, Analyze Fabric, Generate Garment Representation, Virtual Try-On, Identity Preservation, Quality Validation, Upload Result.
- Pillow-based, GPU-free fabric analysis (dominant color / palette / pattern / brightness) and mock garment construction + try-on composite that keeps the person image as its base (face never altered, `DEMO PREVIEW` stamp).
- Identity preservation score (face-region structural overlap) gated by `identity_min_score`.
- `VirtualTryOnProvider` interface with `TryOnInput` / `TryOnOutput`, `build_pipeline()` per provider, and factory `get_provider()` honoring `AI_PROVIDER`/`TRY_ON_PROVIDER`; re-exports pipeline errors from one module (`services/try_on_provider.py`).
- Error taxonomy: `TryOnError` base with `retryable`; `RetryableTryOnError`; `PermanentTryOnError`; subclasses `InputValidationError`, `ProviderConfigurationError`, `FabricGenerationFailed`, `TryOnComposeFailed`, `QualityCheckFailed`, `UploadFailed`.
- `MockVirtualTryOnProvider` runs the real staged pipeline GPU-free; `CatVTON` and `IDM-VTON` providers run the full staged pipeline but require `AI_GARMENT_GENERATION_ENDPOINT` / `AI_TRYON_GENERATION_ENDPOINT`, failing **honestly** with `ProviderConfigurationError` (never faking a result) when unconfigured.
- **`GeminiProvider`** (`gemini`) added - **real AI image generation, no fake data**. Two-stage pipeline driven by Gemini's native `generateContent` REST endpoint (new `services/gemini.py`): fabric swatch -> rendered garment (`GeminiGarmentConstructionStage`), person + garment -> try-on (`GeminiVirtualTryOnStage`), both seeded from the Pillow fabric analysis. Config: `GEMINI_API_KEY` / `GEMINI_MODEL` (`gemini-3.1-flash-image`) / `GEMINI_BASE_URL` / `GEMINI_TIMEOUT`. Without `GEMINI_API_KEY` it fails honestly with `ProviderConfigurationError`.
- Gemini unit tests (`tests/test_gemini.py`): payload builder, MIME sniffing, image extraction, error translation, honest-failure-without-key, full provider generate with mocked API. Provider factory resolves `gemini`.
- **Image-generation backend abstraction** (`services/image_gen.py`): `ImageGenBackend` ABC with `GeminiImageGenBackend` (delegates to `services/gemini.py`) and **new `FluxImageGenBackend`** (FLUX-compatible JSON API: `task`/`model`/`prompt`/`reference_images` -> `{"image": b64}` or raw bytes; `ImageGenNotConfigured` when `FLUX_ENDPOINT` unset). Error taxonomy `ImageGenError` / `ImageGenNotConfigured` / `ImageGenAPIError`; generic pipeline stages `ImageGenGarmentConstructionStage` / `ImageGenVirtualTryOnStage` (map not-configured -> `ProviderConfigurationError`, API errors -> retryable `FabricGenerationFailed` / `TryOnComposeFailed`). Old `GeminiGarmentConstructionStage` / `GeminiVirtualTryOnStage` kept as subclasses for compat.
- **`FluxProvider`** (`flux`) added: same raw-fabric -> garment -> person workflow through the FLUX backend. Factory now resolves `mock | catvton | idmvton | gemini | flux`; IDM-VTON stays experimental. New config `IMAGE_GEN_BACKEND`, `FLUX_ENDPOINT` / `FLUX_API_KEY` / `FLUX_MODEL` / `FLUX_TIMEOUT` (+ `.env.example`).
- **OpenAI image generation live-verified** against the real `gpt-image-1` for the full workflow (1024x1536 PNG; measured face-identity ~0.82 on one run). Added retry/backoff for transient 429/5xx/transport failures. Current blocker is account-side: the workspace has no remaining OpenAI credits (`429: You have no credits remaining`) - earlier failures were transient access-propagation 403s / connection aborts, not code.
- **End-to-end provider/workflow tests** (`tests/test_e2e_pipeline.py`): full customer photo + raw fabric + garment type + style -> generated result through the real provider code and the Celery worker DB path; only the HTTP transport is stubbed (deterministic model substitute). Validates the SAVED result: decodable + >=128px, differs from the source photo, face identity preserved, and the garment band carries the fabric's dominant colour. Plus unit tests `tests/test_image_gen.py` (payloads, base64 parsing, honest unconfigured failures, raw-bytes responses). Total suite **82 passed + 1 skipped** (opt-in live test gated on `VASTRAI_LIVE_E2E=1` + `OPENAI_API_KEY`/`GEMINI_API_KEY`/`FLUX_ENDPOINT` runs the genuine model and validates the real output).
- Celery task `process_try_on_job` rewritten with **claim-based idempotency** (atomic `UPDATE ... WHERE status='QUEUED'`) and **exponential backoff** (`min(60, 5*2**retries)`); resets to `QUEUED` before `self.retry`; `PermanentTryOnError` fails the job immediately with a useful message. (see AI_MODEL.md).
- Job schema + API expose `provider` / `model_version`.

### Tests

- Backend pytest suite: auth, uploads, try-on, provider factory/contract, pipeline, Gemini client/provider, image-gen backend abstraction (Gemini/FLUX/OpenAI), end-to-end provider/worker workflows, and task/idempotency tests; green against an in-memory SQLite DB with mocked broker and ImageKit.

## Current Implementation Status

- The full product loop works end to end using the mock provider: register -> upload photo -> upload fabric -> pick garment + style -> generate -> poll -> result is shown and saved to local history. The result screen shows a YOUR PHOTO / SELECTED FABRIC / GENERATED LOOK strip; the review screen labels the cloth "SELECTED FABRIC".
- The AI pipeline is now staged and provider-driven. Mock runs all seven stages GPU-free; CatVTON/IDM-VTON are wired to the same pipeline but need real endpoints; **Gemini/FLUX run real AI image generation** through the `ImageGenBackend` seam and fail honestly (never a fake result) when unconfigured. `GEMINI_API_KEY` + `AI_PROVIDER=gemini` are set in `backend/.env`; real image generation is **paid-only** on the free tier, so live output waits on billing being enabled.
- Image storage runs on ImageKit when credentials are configured; local dev runs on placeholder URLs.
- History is per-device (AsyncStorage), not synced to the server.

## Known Limitations

- **No real AI provider live yet**: CatVTON and IDM-VTON have no live endpoints configured (`AI_GARMENT_GENERATION_ENDPOINT` / `AI_TRYON_GENERATION_ENDPOINT`); `GEMINI_API_KEY` is set but Gemini image generation is **paid-only** - the free tier returns `429 generate_content_free_tier_requests, limit: 0`. Real output is verified end to end via the opt-in `VASTRAI_LIVE_E2E=1` test once billing is enabled.
- **Gemini is an image editor/generator, not a true garment-warping VTON**: it renders/edits rather than geometrically warping a garment to a body; identity/pose fidelity depends on the model and prompt, hence `IDENTITY_MIN_SCORE` guarding. Live verification is pending a key.
- **Fabric-to-garment generation** needs a real fabric -> garment model endpoint; the mock provider's garment panel is a flat texture sample (clearly labelled `DEMO PREVIEW`), not a true render.
- **Mobile router gaps resolved**: try-on deep links now resolve correctly - home/history empty states and result actions route through `/tryon` (smart dispatcher) and `/camera/person` / `/camera/fabric` for re-capture. The full journey HOME -> GARMENT -> CREATE YOUR LOOK (two-image upload) -> STYLE -> REVIEW -> GENERATE -> PROCESSING -> RESULT is wired end to end.
- **No mobile unit/integration tests**: only `tsc --noEmit` is enforced.
- **History is local-only**: no `GET /history` server endpoint; results are not retrievable on a new device.
- **No async client upload tokens**: `generate_client_upload_token()` in `imagekit.py` returns an empty token/signature (client-side direct upload not implemented).
- **Social login, password reset, and "Save to looks" are stubs** (alerts / "coming soon").
- **Result image re-fetch**: `GET /try-on/{id}/result` requires re-polling; there is no long-polling or webhook push.
- **No response pagination or filtering** on job/media queries.
- **Ceilings**: uploads capped at 15 MB; job polling capped at ~4 minutes on the client before timing out; `max_retries=2` on the job row.

## Next Steps

1. **Verify a real AI provider end to end** - the OpenAI `gpt-image-1` path is implemented and live-verified once; re-run `VASTRAI_LIVE_E2E=1 VASTRAI_LIVE_PROVIDER=openai python -m pytest tests/test_e2e_pipeline.py::test_live_real_generation` once OpenAI credits are added to the account. Gemini remains a fallback once billing is enabled; FLUX via `FLUX_ENDPOINT`.
2. **Add mobile tests** - unit tests for `TryOnContext` / `AuthContext` and the API layer (jest + the SDK 54 toolchain).
3. **Server-side history** - list endpoint (`GET /try-on`), and switch History to it with graceful fallback to local storage.
4. **ImageKit client tokens** - implement real upload token signing for direct-from-device uploads to cut upload latency.
5. **Production hardening** - real secret management, TLS, rate limiting, response pagination, and structured logging around worker failures.
6. **UX details currently stubbed** - social login, password reset, saved-looks persistence.