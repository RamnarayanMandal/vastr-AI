import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["AI_PROVIDER"] = "mock"            # never let the dev .env leak in
os.environ["TRY_ON_PROVIDER"] = "mock"
os.environ["AI_WORKFLOW_ENGINE"] = "pipeline"  # deterministic for tests; langgraph tests override explicitly
os.environ["GEMINI_MODEL"] = "gemini-3.1-flash-image"
os.environ["OPENAI_MODEL"] = "gpt-image-2"
os.environ["OPENROUTER_MODEL"] = "qwen/qwen-image-3"
os.environ["OPENROUTER_FALLBACK_MODEL"] = ""

# Without VASTRAI_LIVE_E2E=1 the real credential/endpoint env is scrubbed so
# unit/integration runs never hit paid APIs. Live mode keeps the .env values
# so opt-in tests can call the genuine models (downloads/uploads stay mocked).
_live = os.environ.get("VASTRAI_LIVE_E2E") == "1"
if not _live:
    os.environ["GEMINI_API_KEY"] = ""
    os.environ["OPENAI_API_KEY"] = ""
    os.environ["AI_GARMENT_GENERATION_ENDPOINT"] = ""
    os.environ["AI_TRYON_GENERATION_ENDPOINT"] = ""

os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["CELERY_BROKER_URL"] = "memory://"
os.environ["CELERY_RESULT_BACKEND"] = "memory://"
os.environ["REDIS_URL"] = "memory://"
os.environ["IMAGEKIT_PUBLIC_KEY"] = ""
os.environ["IMAGEKIT_PRIVATE_KEY"] = ""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import get_current_user
from app.models import User
from app.security import create_access_token

from app.main import app


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db

    _celery_patch = patch(
        "app.router.try_on.process_try_on_job",
        MagicMock(delay=lambda *a, **kw: None),
    )
    _celery_patch.start()

    _imgkit_patch = patch("app.services.imagekit.upload_bytes", return_value=None)
    _imgkit_patch.start()

    _imgkit_upload_patch = patch("app.router.uploads.upload_bytes", return_value=None)
    _imgkit_upload_patch.start()

    with TestClient(app) as c:
        yield c

    _imgkit_upload_patch.stop()
    _imgkit_patch.stop()
    _celery_patch.stop()
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client, db_session):
    user = User(
        full_name="Test User",
        email="test@example.com",
        mobile="9876543210",
    )
    user.set_password("secret123")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}, user


@pytest.fixture()
def sample_user(db_session):
    user = User(
        full_name="Direct User",
        email="direct@example.com",
        mobile="1234567890",
    )
    user.set_password("pass1234")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def mock_http_response():
    """Factory: returns a mock HTTP response with status_code and json()."""
    def _factory(status_code=200, json_data=None):
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = json_data or {}
        resp.text = str(json_data or "")
        return resp
    return _factory
