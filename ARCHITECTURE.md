# VastrAI Architecture

VastrAI is a two-part system: an Expo/React Native mobile app and a FastAPI + Celery backend. The AI model is deliberately isolated behind a provider interface so the rest of the system never talks to a specific model.

## High-Level Diagram

```
┌───────────────────────────────┐
│         Mobile (Expo)         │
│  expo-router screens          │
│  AuthContext  TryOnContext    │
│  src/services/api.ts          │
└──────────────┬────────────────┘
               │ HTTPS / JSON   (Bearer JWT)
               ▼
┌──────────────────────────────────────────────┐
│               Backend (FastAPI)              │
│  app/main.py -> /api/v1 routers             │
│                                              │
│  auth  ─┐                                    │
│  upload ┼──> services/imagekit.py ─────────► ImageKit (or placeholder URL)
│  try-on ┘    deps.get_current_user           │
│              schemas / models / db session   │
└──────────────┬───────────────────────────────┘
               │ .delay(job_id)                 (Redis broker)
               ▼
┌──────────────────────────────────────────────┐
│             Celery worker                    │
│  app/worker/tasks.py                         │
│  process_try_on_job                          │
│    -> services/try_on_provider.generate()    │
│    -> Mock / CatVTON / IDM-VTON              │
│                                               │
│  updates try_on_jobs -> COMPLETED/FAILED      │
└──────────────────────────────────────────────┘
```

Datastores: PostgreSQL (authoritative app data), Redis (Celery broker `:0` + result backend `:1`), ImageKit (blob image storage; absent in dev, placeholder URLs are used).

## Mobile Architecture

### Screens (expo-router)

`app/` mirrors the URL structure:

| Route                    | Purpose                                    |
| ------------------------ | ------------------------------------------ |
| `index`                  | Splash screen with tagline animation       |
| `login`, `register`      | Auth via `/api/v1/auth/*`                  |
| `(tabs)/home`            | Home tab                                   |
| `(tabs)/history`         | Past looks (stored locally in AsyncStorage)|
| `(tabs)/profile`         | Profile tab                                |
| `tryon/{index,garment,style,upload}` | Try-on wizard: gender -> garment -> style -> upload |
| `camera/person`, `camera/fabric` | In-app capture (expo-camera), auto-upload |
| `review`                 | Review inputs before generation            |
| `processing/[jobId]`     | Shows staged animation, polls job status   |
| `processing-error/[jobId]` | Retry / change image on failure          |
| `result/[jobId]`         | Draggable before/after compare + share     |

### Client state

- **AuthContext** (`src/context/AuthContext.tsx`) holds the current user; token + user persisted via AsyncStorage (`storage.ts`).
- **TryOnContext** (`src/context/TryOnContext.tsx`) holds the `TryOnDraft` (gender, garment, style, both image URIs and uploaded asset IDs, job id, status) and drives the state machine below. The draft is persisted so an interrupted flow can resume.

```
IDLE -> UPLOADING_PERSON -> PERSON_UPLOADED
     -> UPLOADING_FABRIC  -> FABRIC_UPLOADED
     -> READY_TO_GENERATE -> QUEUED -> PROCESSING -> COMPLETED
                                               `----> FAILED
```

### API layer

`src/services/api.ts` wraps all HTTP calls:

- `request<T>()` adds the `Authorization: Bearer <token>` header and normalizes errors into `ApiError`.
- `uploadPersonImage(uri)` / `uploadFabricImage(uri)` send multipart/form-data via `fetch` + `FormData`.
- `createTryOnJob(input)`, `getJob(jobId)`, `getJobResult(jobId)` for the job lifecycle.

The base URL comes from `EXPO_PUBLIC_API_URL`, defaulting to `http://localhost:8000/api/v1`.

Garment/style catalogs live in `src/constants/garments.ts` (`garmentsByGender`, `garmentStyles`, `stylesForGarment`).

## Backend Architecture

Layered as **router -> service/dependency -> model**. Workers are a separate process.

```
router/auth.py     router/uploads.py     router/try_on.py
   |                      |                    |
   |  deps.get_current_user (JWT via Authorization header)
   |                      |                    |
   v                      v                    v
 PostgreSQL (models.py)  ImageKit (imagekit.py)   Celery .delay(job_id) -> worker/tasks.py
                                                       |
                                                       v
                                               services/try_on_provider.py
                                                       |
                                              Mock / CatVTON / IDM-VTON
```

- **Routers** (`app/router/`) define endpoints, validate via Pydantic schemas, and enforce ownership (each job/asset is scoped to the authenticated user).
- **Services** (`app/services/`) encapsulate external dependencies: image upload/fallback (`imagekit.py`) and AI inference (`try_on_provider.py`).
- **Worker** (`app/worker/`) is the only place that touches the AI. `process_try_on_job` in `tasks.py` loads the job, marks it `PROCESSING`, calls the provider, stores the result, and marks it `COMPLETED` (or `FAILED` after retries).
- **Config** (`config.py`) is env-driven; selecting the AI provider (`TRY_ON_PROVIDER=mock|catvton|idmvton`) is a simple config change.

## Database Schema

All PKs are UUIDv4. `created_at` defaults to `now()`.

### users

| Column          | Type          | Notes                         |
| --------------- | ------------- | ----------------------------- |
| id              | UUID PK       |                               |
| full_name       | String(120)   | required                      |
| email           | String(255)   | unique, indexed               |
| mobile          | String(20)    | unique, indexed               |
| hashed_password | String(255)   | bcrypt via passlib            |
| created_at      | DateTime      |                               |

### media_assets

| Column            | Type          | Notes                                        |
| ----------------- | ------------- | -------------------------------------------- |
| id                | UUID PK       |                                              |
| user_id           | UUID FK users | owner                                        |
| kind              | String(20)    | `person` \| `fabric` \| `result`             |
| imagekit_file_id  | String(120)   | ImageKit file id (local fallback for dev)    |
| url               | Text          | public image URL                             |
| created_at        | DateTime      |                                              |

### try_on_jobs

| Column            | Type          | Notes                                  |
| ----------------- | ------------- | -------------------------------------- |
| id                | UUID PK       |                                        |
| user_id           | UUID FK users | indexed                                |
| person_image_id   | UUID FK media_assets | the person's photo input         |
| fabric_image_id   | UUID FK media_assets | the cloth / ready garment        |
| garment_type      | String(60)    | e.g. `shirt`, `saree`, `kurta`         |
| garment_style     | String(60)    | e.g. `slim`, `traditional_draping`     |
| gender            | String(10)    | nullable (`MEN`/`WOMEN`/`KIDS`)        |
| status            | String(20)    | `QUEUED` default; indexed              |
| provider          | String(60)    | nullable; filled by worker             |
| model_version     | String(120)   | nullable; filled by worker             |
| error_message     | Text          | nullable                               |
| retry_count       | Integer       | default 0                              |
| max_retries       | Integer       | default 2                              |
| created_at        | DateTime      |                                        |
| started_at        | DateTime      | nullable; set when `PROCESSING`        |
| completed_at      | DateTime      | nullable; set when terminal            |

### try_on_results

| Column            | Type          | Notes                                   |
| ----------------- | ------------- | --------------------------------------- |
| id                | UUID PK       |                                         |
| try_on_job_id     | UUID FK try_on_jobs | indexed, one-to-one with job       |
| result_image_id   | UUID FK media_assets | points at the `result` asset       |
| result_url        | Text          | published image URL                     |
| created_at        | DateTime      |                                         |

A `try_on_jobs` row has at most one `TryOnResult` (`uselist=False`, cascade delete). The result image is also a row in `media_assets` with `kind='result'`, so one storage abstraction covers inputs and outputs.

## Job Lifecycle

```
                    create_try_on (202)
                         │
                         v
  ┌────────────────  QUEUED  ────────────────┐
  │      .delay() enqueues on Redis          │
  │      (broker down -> marked FAILED)       │
  └───────────────────┬──────────────────────┘
                      │ worker picks up job
                      v
                 PROCESSING                    (started_at set)
                      │
                 provider.generate()
                      │
          ┌───────────┴───────────┐
          │ TryOnError            │ other exception
          v                       v
      retry < max_retries?   retries exhausted
      yes / no               yes
        │                      │
        ▼                      ▼
   (re-queue)              FAILED  (error_message set, completed_at)
        │
        └── on success ──► COMPLETED
                           (result asset created,
                            try_on_results row,
                            provider + model_version recorded)
```

Notes:

- Posting a job returns `202 Accepted` immediately with the job row (`status = QUEUED`).
- The worker (`max_retries=3` in Celery, `max_retries=2` on the job row) only retries `TryOnError`, which the contract treats as a "transient, retryable" failure (see AI_MODEL.md).
- Polling: `GET /try-on/{id}` returns the live status; `GET /try-on/{id}/result` returns the result only when `status == COMPLETED`, otherwise `404`.