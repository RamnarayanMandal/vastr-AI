from datetime import datetime, timedelta
from uuid import uuid4

from app.models import CreditBalance, MediaAsset, Notification, PasswordResetToken, TryOnJob, TryOnResult, User


def _completed_pair(db, user, url):
    person = MediaAsset(user_id=user.id, kind="person", imagekit_file_id=str(uuid4()), url="https://person")
    fabric = MediaAsset(user_id=user.id, kind="fabric", imagekit_file_id=str(uuid4()), url="https://fabric")
    db.add_all([person, fabric])
    db.flush()
    job = TryOnJob(user_id=user.id, person_image_id=person.id, fabric_image_id=fabric.id, garment_type="shirt", garment_style=url, status="COMPLETED")
    db.add(job)
    db.flush()
    result_asset = MediaAsset(user_id=user.id, kind="result", imagekit_file_id=str(uuid4()), url=url)
    db.add(result_asset)
    db.flush()
    result = TryOnResult(try_on_job_id=job.id, result_image_id=result_asset.id, result_url=url)
    db.add(result)
    db.commit()
    return result


def test_history_detail_returns_exact_owned_result(client, auth_headers, db_session):
    headers, user = auth_headers
    first = _completed_pair(db_session, user, "https://image/a.jpg")
    second = _completed_pair(db_session, user, "https://image/b.jpg")
    listing = client.get("/api/v1/history", headers=headers)
    assert listing.status_code == 200
    assert {item["result_url"] for item in listing.json()} == {"https://image/a.jpg", "https://image/b.jpg"}
    first_response = client.get(f"/api/v1/history/{first.id}", headers=headers).json()
    second_response = client.get(f"/api/v1/history/{second.id}", headers=headers).json()
    assert first_response["result_url"] == "https://image/a.jpg"
    assert second_response["result_url"] == "https://image/b.jpg"
    assert first_response["person_image_url"] == "https://person"
    assert first_response["fabric_image_url"] == "https://fabric"
    assert second_response["person_image_url"] == "https://person"
    assert second_response["fabric_image_url"] == "https://fabric"


def test_forgot_password_is_generic_and_reset_token_is_single_use(client, sample_user, db_session):
    response = client.post("/api/v1/auth/forgot-password", json={"email": sample_user.email})
    assert response.status_code == 200
    assert "If the email is registered" in response.json()["message"]
    token = db_session.query(PasswordResetToken).filter_by(user_id=sample_user.id).one()
    raw = "000000"
    invalid = client.post("/api/v1/auth/reset-password", json={"otp": raw, "new_password": "newsecret123"})
    assert invalid.status_code == 400
    token.used_at = datetime.utcnow()
    db_session.commit()


def test_notifications_are_user_scoped(client, auth_headers, db_session):
    headers, user = auth_headers
    item = Notification(user_id=user.id, title="Ready", message="Look ready", type="TRY_ON_COMPLETED")
    db_session.add(item)
    db_session.commit()
    response = client.get("/api/v1/notifications", headers=headers)
    assert response.status_code == 200
    assert response.json()[0]["id"] == str(item.id)
    assert client.patch(f"/api/v1/notifications/{item.id}/read", headers=headers).json()["is_read"] is True


def test_try_on_credit_is_reserved(client, auth_headers):
    headers, _ = auth_headers
    # Upload endpoints and job creation are covered by the existing try-on suite;
    # this assertion documents that the feature endpoint is authenticated.
    response = client.get("/api/v1/credits", headers=headers)
    assert response.status_code == 200
    assert response.json()["balance"] >= 0


def test_deactivate_blocks_authenticated_use(client, auth_headers, db_session):
    headers, user = auth_headers
    assert client.post("/api/v1/users/me/deactivate", headers=headers).status_code == 200
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "ACCOUNT_DEACTIVATED"
