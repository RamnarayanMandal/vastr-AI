# VastrAI

**See It. Try It. Wear It.**

VastrAI is an AI Virtual Try-On app for clothing and fabric shops. A customer uploads a photo of themselves and a photo of a cloth, fabric, or ready-made garment, picks the garment type and style, and the AI generates a realistic preview of the customer wearing the garment made from that fabric.

## Product Overview

- **Customers** upload two images: their own photo and the cloth/fabric they are considering.
- **Garment selection** narrows the result: garment type (shirt, saree, kurta, ...) and style (slim fit, traditional drape, ...), split by gender (Men / Women / Kids).
- **The backend** stores images, queues an AI inference job, and exposes a progress polling API.
- **The AI** is abstracted behind a `VirtualTryOnProvider` interface. Development uses a deterministic mock provider; OpenAI (gpt-image-1) and Gemini are wired in as production-ready generators for the raw-fabric -> garment -> person workflow, and CatVTON/IDM-VTON (plus FLUX) remain as alternative endpoint providers.

## Quick Start

### Mobile (React Native / Expo)

```bash
cd mobile
npm install
npx expo start
```

Set the API base URL before starting (defaults to `http://localhost:8000/api/v1`):

```bash
# macOS / Linux
EXPO_PUBLIC_API_URL=http://192.168.x.x:8000/api/v1 npx expo start
# Windows PowerShell
$env:EXPO_PUBLIC_API_URL="http://192.168.x.x:8000/api/v1"; npx expo start
```

Use the LAN IP of your machine when running on a physical device.

### Backend (API + Worker)

1. Start PostgreSQL and Redis:

```bash
cd backend
docker compose up -d postgres redis
```

2. Apply the database migrations:

```bash
alembic upgrade head
```

3. (Optional) Copy `.env.example` to `.env` and adjust values. The defaults point at the dockerized Postgres/Redis.

4. Run the API **and** the worker with a single command (one terminal, one clean setup):

```powershell
cd backend
.\run_dev.ps1        # starts uvicorn (foreground) + ONE Celery worker (background)
```

This starts exactly one uvicorn server and exactly one worker — nothing is
auto-spawned from inside the web server. Use `.\run_dev.ps1 -NoWorker` to run
the API alone, or `-NoReload` to disable hot reload.

> Alternatively, start everything containerized:
> ```bash
> cd backend && docker compose up -d
> ```

Interactive API docs are available at `http://localhost:8000/docs`.

## Project Structure

```
VastraView/
├── mobile/                        # React Native + Expo SDK 54 (expo-router)
│   ├── app/                       # expo-router screens
│   │   ├── _layout.tsx            # Root layout (Auth + TryOn providers)
│   │   ├── index.tsx              # Splash screen
│   │   ├── login.tsx / register.tsx
│   │   ├── (tabs)/                # Home, History, Profile
│   │   ├── tryon/                 # Garment, Style, Upload flow
│   │   ├── camera/                # Person & fabric capture
│   │   ├── review.tsx             # Review before generating
│   │   ├── processing/[jobId].tsx # Poll job status
│   │   ├── processing-error/[jobId].tsx
│   │   └── result/[jobId].tsx     # Before/after compare view
│   └── src/
│       ├── components/            # AppButton, BottomNav, ImageUploadCard
│       ├── constants/garments.ts  # Genders, garment types, styles
│       ├── context/               # AuthContext, TryOnContext
│       ├── services/              # api.ts, storage.ts (AsyncStorage)
│       ├── theme/                 # colors, typography, spacing, shadows
│       └── types/                 # Shared TypeScript types
├── backend/                       # FastAPI + SQLAlchemy + Celery
│   ├── app/
│   │   ├── main.py                # FastAPI app, routers, /health
│   │   ├── config.py              # Settings (env-driven)
│   │   ├── database.py            # Engine, SessionLocal, Base
│   │   ├── models.py              # User, MediaAsset, TryOnJob, TryOnResult
│   │   ├── schemas.py             # Pydantic request/response models
│   │   ├── security.py            # JWT create/decode
│   │   ├── deps.py                # get_current_user
│   │   ├── router/                # auth.py, uploads.py, try_on.py
│   │   ├── services/              # try_on_provider.py, imagekit.py
│   │   └── worker/                # celery_app.py, tasks.py
│   ├── alembic/                   # Migrations (001_initial)
│   ├── tests/                     # pytest suite
│   ├── docker-compose.yml         # postgres, redis, api, worker
│   ├── Dockerfile / Dockerfile.worker
│   └── requirements.txt
└── docs/                          # Empty (docs live at repo root)
```

## Tech Stack

| Layer        | Technology                                                        |
| ------------ | ----------------------------------------------------------------- |
| Mobile       | React Native 0.81, Expo SDK 54, expo-router 6, TypeScript 5.9     |
| Mobile state | React Context (AuthContext, TryOnContext), AsyncStorage           |
| Backend      | Python 3.12, FastAPI 0.115, Pydantic 2, Uvicorn                   |
| ORM          | SQLAlchemy 2.0, Alembic migrations                                |
| Database     | PostgreSQL 16                                                     |
| Queue / jobs | Celery 5.4, Redis 7 (broker + result backend)                     |
| Auth         | JWT (python-jose), bcrypt (passlib)                               |
| Media        | ImageKit (fallback to placeholder URLs without credentials)       |
| AI           | `VirtualTryOnProvider` abstraction (mock / CatVTON / IDM-VTON / Gemini / FLUX / OpenAI) |
| Tests        | pytest (backend), `tsc --noEmit` typecheck (mobile)               |

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture, job lifecycle, database schema
- [API.md](API.md) - Endpoint reference with request/response examples
- [AI_MODEL.md](AI_MODEL.md) - The AI provider abstraction and available models
- [TESTING.md](TESTING.md) - How to run and what the tests cover
- [ENGINEERING_PROGRESS.md](ENGINEERING_PROGRESS.md) - MVP status, limitations, next steps