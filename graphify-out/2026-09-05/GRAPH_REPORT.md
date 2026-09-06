# Graph Report - VastraView  (2026-09-03)

## Corpus Check
- 96 files · ~72,351 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 937 nodes · 2344 edges · 45 communities (33 shown, 7 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 148 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Backend Infrastructure
- Fabric Analysis Engine
- Image Generation Backends
- Workflow Orchestration
- Job Queue & Data Models
- Mobile Expo Dependencies
- Virtual Try-On Providers
- Mobile Camera & Review UI
- Mobile App Configuration
- AI Model Documentation
- AI Provider Abstraction
- Pipeline & Garment Construction
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 38
- Community 39
- Community 44

## God Nodes (most connected - your core abstractions)
1. `TryOnInput` - 32 edges
2. `MockVirtualTryOnProvider` - 28 edges
3. `GeminiProvider` - 26 edges
4. `_process_job()` - 25 edges
5. `synthesize_fabric_bytes()` - 24 edges
6. `ValidateInputsStage` - 24 edges
7. `FluxImageGenBackend` - 23 edges
8. `OpenAIImageGenBackend` - 23 edges
9. `synthesize_person_bytes()` - 23 edges
10. `useTryOn()` - 23 edges

## Surprising Connections (you probably didn't know these)
- `process_try_on_job task` --references--> `VirtualTryOnProvider`  [EXTRACTED]
  ARCHITECTURE.md → AI_MODEL.md
- `process_try_on_job task` --references--> `Exponential Backoff`  [EXTRACTED]
  ARCHITECTURE.md → AI_MODEL.md
- `Live E2E Test` --references--> `OpenAI gpt-image-1`  [EXTRACTED]
  TESTING.md → AI_MODEL.md
- `Live E2E Test` --references--> `OPENAI_API_KEY`  [EXTRACTED]
  TESTING.md → AI_MODEL.md
- `test_e2e_worker_gemini_job_completes_and_validates()` --uses--> `TryOnResult`  [INFERRED]
  backend/tests/test_e2e_pipeline.py → backend/app/models.py

## Import Cycles
- None detected.

## Communities (45 total, 7 thin omitted)

### Community 0 - "Backend Infrastructure"
Cohesion: 0.05
Nodes (64): AuthResponse, get_settings(), Settings, Base, get_db(), get_current_user(), Session, User (+56 more)

### Community 1 - "Fabric Analysis Engine"
Cohesion: 0.06
Nodes (60): analyze_fabric(), _draw_garment_mask(), FabricAnalysis, _hex(), identity_metrics(), _mock_garment_panel(), _mock_tryon_compose(), GPU-free placeholder 'customer' used by the mock provider offline. (+52 more)

### Community 2 - "Image Generation Backends"
Cohesion: 0.07
Nodes (40): build_garment_prompt(), build_tryon_prompt(), FluxImageGenBackend, GeminiImageGenBackend, get_image_gen_backend(), ImageGenAPIError, ImageGenError, ImageGenNotConfigured (+32 more)

### Community 3 - "Workflow Orchestration"
Cohesion: 0.10
Nodes (49): Any, _brief(), build_workflow_graph(), _get_provider(), _log(), _make_node(), _map_provider_error(), node_analyze_fabric() (+41 more)

### Community 4 - "Job Queue & Data Models"
Cohesion: 0.11
Nodes (44): MediaAsset, TryOnJob, TryOnResult, Transient failure (model timeout, upload hiccup) - safe to retry., RetryableTryOnError, _backoff(), _claim_job(), _fail() (+36 more)

### Community 5 - "Mobile Expo Dependencies"
Cohesion: 0.04
Nodes (46): expo, expo-camera, expo-constants, expo-file-system, expo-font, expo-image-picker, expo-linking, expo-router (+38 more)

### Community 6 - "Virtual Try-On Providers"
Cohesion: 0.11
Nodes (26): TryOnInput, CatVTONProvider, get_provider(), IDMVTONProvider, MockVirtualTryOnProvider, Deterministic, no-GPU provider for tests and local development. Runs the real…, Test helper: make the next generation raise TryOnError., CatVTON-based provider. CatVTON warps a ready-made garment onto a person's… (+18 more)

### Community 7 - "Mobile Camera & Review UI"
Cohesion: 0.12
Nodes (24): ClothCameraScreen(), styles, PersonCameraScreen(), styles, ProcessingErrorScreen(), styles, ReviewScreen(), styles (+16 more)

### Community 8 - "Mobile App Configuration"
Cohesion: 0.06
Nodes (31): backgroundColor, foregroundImage, adaptiveIcon, edgeToEdgeEnabled, package, permissions, predictiveBackGestureEnabled, expo (+23 more)

### Community 9 - "AI Model Documentation"
Cohesion: 0.13
Nodes (30): Service: gemini, Service: image_gen, Service: pipeline, CatVTON, CatVTONProvider, Fabric Analysis, Fabric-to-Garment, FluxProvider (+22 more)

### Community 10 - "AI Provider Abstraction"
Cohesion: 0.12
Nodes (21): AIProvider, AIProviderAPIError, AIProviderError, AIProviderNotConfigured, GeminiImageProvider, get_ai_provider(), OpenAIImageProvider, Exception (+13 more)

### Community 11 - "Pipeline & Garment Construction"
Cohesion: 0.10
Nodes (16): download_url(), Download an image from a URL (used to fetch the AI result for storage)., FabricGenerationFailed, GarmentConstructionStage, PipelineContext, PipelineStage, ProviderConfigurationError, Build a garment representation from the fabric (abstract). (+8 more)

### Community 12 - "Community 12"
Cohesion: 0.13
Nodes (20): SplashScreen(), styles, LoginScreen(), styles, RegisterScreen(), styles, filters, HistoryScreen() (+12 more)

### Community 13 - "Community 13"
Cohesion: 0.13
Nodes (23): ProcessingScreen(), STAGES, styles, EMPTY, TryOnContext, TryOnContextValue, TryOnProvider(), ApiError (+15 more)

### Community 14 - "Community 14"
Cohesion: 0.16
Nodes (18): ImageGenBackend, Try the garment on the person while preserving identity/pose., Render a garment image from the raw fabric swatch., AnalyzeFabricStage, IdentityPreservationStage, ImageGenGarmentConstructionStage, ImageGenVirtualTryOnStage, Render the garment from the raw fabric using a real image-gen backend. The… (+10 more)

### Community 15 - "Community 15"
Cohesion: 0.16
Nodes (22): InputValidationError, MockGarmentConstructionStage, MockVirtualTryOnStage, PermanentTryOnError, Exception, Base error for the AI try-on pipeline., Flat garment panel sampled from the fabric texture (development only)., Permanent failure (bad input, missing configuration) - do not retry. (+14 more)

### Community 16 - "Community 16"
Cohesion: 0.14
Nodes (23): Alembic Migrations, Backend Config, Dependencies (get_current_user), Router: auth, Router: try_on, Router: uploads, Pydantic Schemas, Service: try_on_provider (+15 more)

### Community 17 - "Community 17"
Cohesion: 0.11
Nodes (21): Database Models, FastAPI App, Security (JWT/bcrypt), Service: imagekit, Celery Worker, VastrAI, Alembic, Celery 5.4 (+13 more)

### Community 18 - "Community 18"
Cohesion: 0.17
Nodes (21): _build_payload(), _extract_image_bytes(), GeminiAPIError, GeminiError, GeminiNotConfigured, generate_image(), _mime_type(), Exception (+13 more)

### Community 19 - "Community 19"
Cohesion: 0.13
Nodes (11): styles, GarmentScreen(), styles, bottomNav, GarmentDefinition, GarmentOption, garmentsByGender, garmentStyles (+3 more)

### Community 20 - "Community 20"
Cohesion: 0.23
Nodes (14): ResultScreen(), categories, HomeScreen(), styles, AuthContext, AuthContextValue, AuthProvider(), clearToken() (+6 more)

### Community 21 - "Community 21"
Cohesion: 0.21
Nodes (12): process_try_on_job task, API Endpoints, Claim-Based Idempotency, Exponential Backoff, JWT Authentication, MediaAsset, PermanentTryOnError, RetryableTryOnError (+4 more)

### Community 22 - "Community 22"
Cohesion: 0.19
Nodes (8): HttpGarmentConstructionStage, HttpVirtualTryOnStage, QualityCheckFailed, QualityValidationStage, Ask a fabric -> garment generation service to build the garment. Requires…, Warp + compose a ready garment onto the person via an external VTON service…, The generated image failed quality validation., test_quality_validation_rejects_tiny_image()

### Community 23 - "Community 23"
Cohesion: 0.24
Nodes (11): FLUX Image API, Gemini Image Model, FLUX_ENDPOINT, GEMINI_API_KEY, GEMINI_MODEL, pytest, TypeScript, Backend Test Suite (+3 more)

### Community 24 - "Community 24"
Cohesion: 0.25
Nodes (4): LangChain-backed prompt templates for garment + try-on generation. Providers…, Human-readable description of the raw fabric analysis., Structured prompt payload: ``{"garment": ..., "tryon": ...}``., VastrAIPrompts

### Community 25 - "Community 25"
Cohesion: 0.27
Nodes (9): garment_prompts(), Human-readable fabric descriptive text used to seed generation prompts., build_garment_prompt(), build_tryon_prompt(), fabric_descriptions(), Prompt construction for the VastrAI image generation workflow. Uses LangChain…, Return the fabric description dict used to seed prompts., Module-level convenience mirror of the existing ``image_gen`` helper. (+1 more)

### Community 26 - "Community 26"
Cohesion: 0.31
Nodes (6): _register(), test_login_success(), test_login_wrong_password(), test_register_duplicate_email(), test_register_duplicate_mobile(), test_register_success()

### Community 28 - "Community 28"
Cohesion: 0.39
Nodes (7): Celery App, Docker API Service, Docker Postgres, Docker Redis, Docker Worker Service, PostgreSQL 16, Redis 7

### Community 29 - "Community 29"
Cohesion: 0.36
Nodes (5): _jpeg_bytes(), _png_bytes(), test_upload_fabric_success(), test_upload_person_success(), test_upload_unauthenticated()

### Community 31 - "Community 31"
Cohesion: 0.33
Nodes (5): ApiJob, AuthResponse, JobStatus, TryOnStatus, User

### Community 32 - "Community 32"
Cohesion: 0.40
Nodes (3): Pipeline, Ordered stages executed against a single TryOnInput., Return the ordered pipeline for this provider.

### Community 34 - "Community 34"
Cohesion: 0.50
Nodes (5): Adaptive Icon (Android), Favicon, App Icon, App Logo, Splash Screen Icon

### Community 35 - "Community 35"
Cohesion: 0.40
Nodes (4): compilerOptions, strict, extends, expo/tsconfig.base

## Ambiguous Edges - Review These
- `App Logo` → `Splash Screen Icon`  [AMBIGUOUS]
  mobile/assets/splash-icon.png · relation: conceptually_related_to

## Knowledge Gaps
- **116 isolated node(s):** `styles`, `name`, `slug`, `version`, `orientation` (+111 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 315 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `App Logo` and `Splash Screen Icon`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `VastrAIPrompts` connect `Community 24` to `Workflow Orchestration`, `Community 25`, `AI Provider Abstraction`, `Image Generation Backends`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Why does `OpenAIImageGenBackend` connect `Image Generation Backends` to `Fabric Analysis Engine`, `Workflow Orchestration`, `Community 14`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Why does `GeminiImageGenBackend` connect `Image Generation Backends` to `Community 18`, `Pipeline & Garment Construction`, `Community 14`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `TryOnInput` (e.g. with `CatVTONProvider` and `FluxProvider`) actually correct?**
  _`TryOnInput` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `MockVirtualTryOnProvider` (e.g. with `AnalyzeFabricStage` and `IdentityPreservationStage`) actually correct?**
  _`MockVirtualTryOnProvider` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `GeminiProvider` (e.g. with `GeminiImageGenBackend` and `ImageGenBackend`) actually correct?**
  _`GeminiProvider` has 14 INFERRED edges - model-reasoned connections that need verification._