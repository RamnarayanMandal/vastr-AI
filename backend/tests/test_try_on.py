from app.models import MediaAsset, TryOnJob, TryOnResult
import uuid


def _jpeg_bytes():
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (201, 169, 106)).save(buf, format="JPEG")
    buf.seek(0)
    return buf


def _upload_person(client, headers):
    resp = client.post(
        "/api/v1/upload/person",
        files={"file": ("person.jpg", _jpeg_bytes(), "image/jpeg")},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["image_id"]


def _upload_fabric(client, headers):
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (13, 11, 26)).save(buf, format="PNG")
    buf.seek(0)
    resp = client.post(
        "/api/v1/upload/fabric",
        files={"file": ("fabric.png", buf, "image/png")},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["image_id"]


def test_create_try_on_job_success(client, auth_headers):
    headers, user = auth_headers
    person_id = _upload_person(client, headers)
    fabric_id = _upload_fabric(client, headers)
    resp = client.post(
        "/api/v1/try-on",
        json={
            "person_image_id": person_id,
            "fabric_image_id": fabric_id,
            "garment_type": "shirt",
            "garment_style": "casual",
        },
        headers=headers,
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] in ("QUEUED", "FAILED")
    assert body["garment_type"] == "shirt"


def test_create_try_on_job_missing_person(client, auth_headers):
    headers, user = auth_headers
    fabric_id = _upload_fabric(client, headers)
    resp = client.post(
        "/api/v1/try-on",
        json={
            "person_image_id": "00000000-0000-0000-0000-000000000000",
            "fabric_image_id": fabric_id,
            "garment_type": "dress",
            "garment_style": "formal",
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_create_try_on_job_missing_fabric(client, auth_headers):
    headers, user = auth_headers
    person_id = _upload_person(client, headers)
    resp = client.post(
        "/api/v1/try-on",
        json={
            "person_image_id": person_id,
            "fabric_image_id": "00000000-0000-0000-0000-000000000000",
            "garment_type": "jacket",
            "garment_style": "sporty",
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_get_job_success(client, auth_headers):
    headers, user = auth_headers
    person_id = _upload_person(client, headers)
    fabric_id = _upload_fabric(client, headers)
    create_resp = client.post(
        "/api/v1/try-on",
        json={
            "person_image_id": person_id,
            "fabric_image_id": fabric_id,
            "garment_type": "kurta",
            "garment_style": "traditional",
        },
        headers=headers,
    )
    job_id = create_resp.json()["id"]
    resp = client.get(f"/api/v1/try-on/{job_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == job_id


def test_get_job_not_found(client, auth_headers):
    headers, _ = auth_headers
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/api/v1/try-on/{fake_id}", headers=headers)
    assert resp.status_code == 404


def test_get_result_not_ready(client, auth_headers):
    headers, _ = auth_headers
    person_id = _upload_person(client, headers)
    fabric_id = _upload_fabric(client, headers)
    create_resp = client.post(
        "/api/v1/try-on",
        json={
            "person_image_id": person_id,
            "fabric_image_id": fabric_id,
            "garment_type": "saree",
            "garment_style": "elegant",
        },
        headers=headers,
    )
    job_id = create_resp.json()["id"]
    resp = client.get(f"/api/v1/try-on/{job_id}/result", headers=headers)
    assert resp.status_code == 404


def test_get_result_ready_returns_url(client, auth_headers, db_session):
    """A COMPLETED job with a persisted result row returns 200 + the result
    URL. Regression test for the TryOnResultOut model_validate bug."""
    headers, user = auth_headers
    person_id = _upload_person(client, headers)
    fabric_id = _upload_fabric(client, headers)
    create_resp = client.post(
        "/api/v1/try-on",
        json={
            "person_image_id": person_id,
            "fabric_image_id": fabric_id,
            "garment_type": "shirt",
            "garment_style": "casual",
        },
        headers=headers,
    )
    job_id = create_resp.json()["id"]

    job = db_session.query(TryOnJob).filter(TryOnJob.id == uuid.UUID(job_id)).one()
    job.status = "COMPLETED"
    result_asset = MediaAsset(
        user_id=user.id,
        kind="result",
        imagekit_file_id="f-result",
        url="https://ik.imagekit.io/vastrai/look.jpg",
    )
    db_session.add(result_asset)
    db_session.flush()
    db_session.add(
        TryOnResult(
            try_on_job_id=job.id,
            result_image_id=result_asset.id,
            result_url="https://ik.imagekit.io/vastrai/look.jpg",
        )
    )
    db_session.commit()

    resp = client.get(f"/api/v1/try-on/{job_id}/result", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["result_url"] == "https://ik.imagekit.io/vastrai/look.jpg"
