from app.models import User


def _register(client, **overrides):
    payload = {
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "mobile": "5551234567",
        "password": "strongpass",
    }
    payload.update(overrides)
    return client.post("/api/v1/auth/register", json=payload)


def test_register_success(client):
    resp = _register(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"]
    assert body["user"]["email"] == "jane@example.com"


def test_register_duplicate_email(client):
    _register(client)
    resp = _register(client, mobile="9999999999")
    assert resp.status_code == 409


def test_register_duplicate_mobile(client):
    _register(client)
    resp = _register(client, email="other@example.com")
    assert resp.status_code == 409


def test_login_success(client, db_session):
    _register(client)
    resp = client.post(
        "/api/v1/auth/login",
        json={"identifier": "jane@example.com", "password": "strongpass"},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_login_wrong_password(client, db_session):
    _register(client)
    resp = client.post(
        "/api/v1/auth/login",
        json={"identifier": "jane@example.com", "password": "wrongpass"},
    )
    assert resp.status_code == 401


def test_login_nonexistent_user(client, db_session):
    resp = client.post(
        "/api/v1/auth/login",
        json={"identifier": "ghost@example.com", "password": "pass123"},
    )
    assert resp.status_code == 401


def test_get_me_authenticated(client, auth_headers):
    headers, user = auth_headers
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == user.email


def test_get_me_unauthenticated(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
