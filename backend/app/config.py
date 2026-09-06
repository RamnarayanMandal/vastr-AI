from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "VastrAI API"
    environment: str = "development"
    api_prefix: str = "/api/v1"

    # Security / JWT
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Database
    database_url: str = "postgresql+psycopg2://vastrai:vastrai@localhost:5434/vastrai"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ImageKit
    imagekit_public_key: str = ""
    imagekit_private_key: str = ""
    imagekit_url_endpoint: str = ""
    imagekit_use_private: bool = False

    # Storage folders
    person_folder: str = "/vastrai/person/"
    fabric_folder: str = "/vastrai/fabric/"
    results_folder: str = "/vastrai/results/"

    # AI Provider (mock | catvton | idmvton | gemini | flux | openai | openrouter)
    ai_provider: str = "mock"            # AI_PROVIDER (preferred)
    try_on_provider: str = "mock"        # legacy TRY_ON_PROVIDER fallback

    # Workflow orchestration engine (pipeline | langgraph).
    # Default 'pipeline' is the existing stage loop; 'langgraph' runs the
    # LangGraph state machine (services.workflow) inside the worker.
    # The canonical env var is AI_WORKFLOW_ENGINE (documented in .env / README);
    # it must be aliased because the field's auto-uppercased name (WORKFLOW_ENGINE)
    # would otherwise never match, silently leaving the engine on 'pipeline'.
    workflow_engine: str = Field(
        default="pipeline",
        validation_alias=AliasChoices("AI_WORKFLOW_ENGINE", "WORKFLOW_ENGINE"),
    )

    # Image generation backend override used by services.image_gen
    image_gen_backend: str = ""          # IMAGE_GEN_BACKEND (gemini | flux | openai)

    # FLUX (real AI image generation via a FLUX-compatible image API).
    # Empty endpoint = the FLUX provider fails honestly with
    # ProviderConfigurationError - never fakes a result.
    flux_endpoint: str = ""              # FLUX_ENDPOINT
    flux_api_key: str = ""               # FLUX_API_KEY
    flux_model: str = "flux-dev"         # FLUX_MODEL
    flux_timeout: float = 300.0          # FLUX_TIMEOUT

    # Gemini (real AI image generation). Unset key = the Gemini provider fails
    # honestly with ProviderConfigurationError - never fakes a result.
    gemini_api_key: str = ""             # GEMINI_API_KEY
    gemini_model: str = "gemini-3.1-flash-image"      # GEMINI_MODEL
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"  # GEMINI_BASE_URL
    gemini_timeout: float = 180.0        # GEMINI_TIMEOUT

    # OpenAI (real AI image generation via the Images API, gpt-image-2).
    # Unset key = the OpenAI provider fails honestly with
    # ProviderConfigurationError - never fakes a result.
    openai_api_key: str = ""             # OPENAI_API_KEY
    openai_model: str = "gpt-image-2"    # OPENAI_MODEL
    openai_base_url: str = "https://api.openai.com/v1"  # OPENAI_BASE_URL
    openai_timeout: float = 300.0        # OPENAI_TIMEOUT

    # OpenRouter (real AI image generation via the OpenRouter Image API).
    # The standard Qwen image-editing model is the default for normal users.
    # NOTE: the canonical OpenRouter slug is "qwen/qwen-image-3" - the ".0"
    # suffix is NOT a valid model ID (returns 404 and forces the fallback).
    # The premium fallback is opt-in ONLY: nothing is set by default so normal
    # requests never silently upgrade to a more expensive model. Set
    # OPENROUTER_FALLBACK_MODEL explicitly to enable it.
    openrouter_api_key: str = ""                 # OPENROUTER_API_KEY
    openrouter_model: str = "qwen/qwen-image-3"  # OPENROUTER_MODEL (standard try-on model)
    openrouter_fallback_model: str = ""          # OPENROUTER_FALLBACK_MODEL (opt-in premium)
    openrouter_base_url: str = "https://openrouter.ai/api/v1"  # OPENROUTER_BASE_URL
    openrouter_timeout: float = 300.0            # OPENROUTER_TIMEOUT
    openrouter_num_images: int = 1                # default one output image to keep cost down

    # Real-model endpoints (empty = the CatVTON/IDM-VTON pipeline fails
    # honestly with ProviderConfigurationError instead of faking a result).
    garment_generation_endpoint: str = ""   # AI_GARMENT_GENERATION_ENDPOINT
    tryon_generation_endpoint: str = ""     # AI_TRYON_GENERATION_ENDPOINT

    # Pipeline quality / retry behaviour
    identity_min_score: float = 0.0         # 0 disables the identity gate
    try_on_max_retries: int = 4             # per-job Celery retries
    retry_backoff_base: int = 5             # seconds, 5 * 2**retries
    retry_max_delay: int = 60               # cap in seconds

    # CORS
    cors_origins: str = "*"

    # Password reset email provider. Empty provider is development-safe and
    # logs only the generated link server-side; production should configure a
    # transactional provider such as Resend.
    email_provider: str = "gmail"
    email_from: str = "VastrAI <ramnarayan84@gmail.com>"
    email_api_key: str = ""
    password_reset_url: str = "vastrai://reset-password"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""
    google_sender_email: str = ""
    initial_ai_credits: int = 10
    try_on_credit_cost: int = 1


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()