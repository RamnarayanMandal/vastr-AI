# VastrAI Testing

## Mobile

The mobile app has no runtime unit tests yet; the enforced check is the TypeScript typecheck.

```bash
cd mobile
npm run typecheck
```

This runs `tsc --noEmit` with `strict: true` (the `tsconfig.json` extends `expo/tsconfig.base`). Run it after any change to `mobile/` to keep the codebase free of type errors.

## Backend

### Setup

```bash
cd backend
pip install -r requirements.txt     # includes pytest and pytest-asyncio
```

### Run

```bash
pytest
```

The suite runs against an in-memory SQLite database with `TRY_ON_PROVIDER=mock`. `conftest.py`:

- Overrides `DATABASE_URL` to `sqlite:///:memory:` before `app.database` is imported, and uses a `StaticPool` session per test.
- Creates the schema via `Base.metadata.create_all`.
- Swaps `get_db` for the test session and stubs `process_try_on_job.delay` and `imagekit.upload_bytes` so no Redis, Postgres, ImageKit, or worker is required.

### What the tests cover

| File                   | Coverage                                                                                          |
| ---------------------- | ------------------------------------------------------------------------------------------------- |
| `test_auth.py`         | Register success (201), duplicate email/mobile (409), login success, wrong password and unknown user (401), `GET /auth/me` authenticated/not (200/401) |
| `test_uploads.py`      | Person/fabric upload success, invalid content type (400), oversized file (413), unauthenticated (401) |
| `test_try_on.py`       | Create job (202, status QUEUED/FAILED), missing person/fabric images (400), job lookup success and 404, result returns 404 until completed |
| `test_provider.py`     | Mock provider generates valid output and records `model_version`/`provider`; `get_provider` factory resolves mock/catvton/idmvton/gemini/flux/openai/default/unknown; CatVTON/IDM-VTON/Gemini fail honestly when unconfigured |
| `test_gemini.py`       | Gemini client: payload builder, MIME sniffing, image extraction, error translation, honest failure without key |
| `test_image_gen.py`    | Backend abstraction: Gemini/FLUX/OpenAI payloads, base64 parsing, raw-bytes responses, honest `ImageGenNotConfigured` failures |
| `test_e2e_pipeline.py` | Full raw-fabric -> garment -> person workflow through provider + Celery worker DB path (transport-stubbed). Validates the saved result: decodable, >=128px, differs from the customer photo, face identity preserved, fabric dominant colour present. Includes opt-in **live** test against real OpenAI/Gemini/FLUX |
| `test_models.py`       | User password set/verify with bcrypt, full user creation defaults |

### Live (real model) verification

The opt-in live test runs the genuine Gemini/FLUX model (no transport stubbing) and validates the actual generated output:

```bash
set VASTRAI_LIVE_E2E=1 && pytest tests/test_e2e_pipeline.py::test_live_real_generation
```

Requires `OPENAI_API_KEY` and/or `GEMINI_API_KEY` (Gemini image generation requires billing) and/or `FLUX_ENDPOINT`. Downloads/uploads stay mocked so the test isolates model quality.

### Notes

- The try-on router test asserts a created job is `QUEUED` or `FAILED` - the Celery `.delay()` is stubbed, so the worker itself is not exercised in pytest. End-to-end worker behavior is verified manually against a running Celery worker with the mock provider.
- To exercise a real provider end to end, run Postgres/Redis, the API, and `celery -A app.worker.celery_app worker -l info -Q vastrai.tryon`, then create a job via the API. `TRY_ON_PROVIDER` controls which provider runs.