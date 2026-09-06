# VastrAI API

Base URL: `http://localhost:8000` - all endpoint paths carry the `/api/v1` prefix.

Authentication: send `Authorization: Bearer <access_token>` for protected endpoints. The token is a JWT and defaults to a 7-day expiry.

Errors: FastAPI returns `{ "detail": "<message>" }` with the appropriate status code.

| Method | Path              | Auth | Description                                  |
| ------ | ----------------- | ---- | -------------------------------------------- |
| POST   | `/auth/register`  | no   | Create an account, returns token + user      |
| POST   | `/auth/login`     | no   | Login with email or mobile, returns token + user |
| GET    | `/auth/me`        | yes  | Current user profile                         |
| POST   | `/upload/person`  | yes  | Upload the customer's photo (multipart `file`) |
| POST   | `/upload/fabric`  | yes  | Upload the cloth/garment photo (multipart `file`) |
| POST   | `/try-on`         | yes  | Create a try-on job (202 on accept)          |
| GET    | `/try-on/{id}`    | yes  | Poll a job's status                          |
| GET    | `/try-on/{id}/result` | yes | Fetch the generated result image (404 until ready) |
| GET    | `/health`         | no   | Service health check                         |

Uploads: accepted content types are `image/jpeg`, `image/png`, `image/webp`, `image/heic`; maximum file size is 15 MB. Without ImageKit credentials the API persists placeholder URLs so the pipeline still works in dev.

---

## POST /auth/register

Create an account. Returns a JWT immediately.

**Request**

```json
{
  "full_name": "Jane Doe",
  "email": "jane@example.com",
  "mobile": "5551234567",
  "password": "strongpass"
}
```

**201 Created**

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": {
    "id": "2a1f0d4b-7b2e-4f21-9c5e-3b81c6d9f20a",
    "full_name": "Jane Doe",
    "email": "jane@example.com",
    "mobile": "5551234567"
  }
}
```

**Errors** - `409` if email or mobile already exists.

---

## POST /auth/login

Login with either email or mobile number.

**Request**

```json
{
  "identifier": "jane@example.com",
  "password": "strongpass"
}
```

**200 OK** - same shape as register (`access_token`, `token_type`, `user`).

**Errors** - `401` for unknown identifier or wrong password.

---

## GET /auth/me

Requires bearer token.

**200 OK**

```json
{
  "id": "2a1f0d4b-7b2e-4f21-9c5e-3b81c6d9f20a",
  "full_name": "Jane Doe",
  "email": "jane@example.com",
  "mobile": "5551234567"
}
```

**Errors** - `401` with missing/invalid token.

---

## POST /upload/person

Multipart form upload with field name `file`.

**Request**

```
Content-Type: multipart/form-data
Authorization: Bearer <token>
file: <customer photo>
```

**200 OK**

```json
{
  "image_id": "5b3a4c6d-9e1f-4a2b-8c3d-7e0f1a2b3c4d",
  "url": "https://ik.imagekit.io/your-endpoint/vastrai/person/abc123.jpg"
}
```

**Errors** - `400` unsupported content type or `413` file too large (over 15 MB), `401` unauthenticated.

---

## POST /upload/fabric

Identical to `/upload/person` but stores the cloth/garment image under the fabric folder.

**200 OK**

```json
{
  "image_id": "f9d8e7c6-b5a4-4932-81f0-e2d3c4b5a697",
  "url": "https://ik.imagekit.io/your-endpoint/vastrai/fabric/xyz789.jpg"
}
```

---

## POST /try-on

Create a try-on job from two previously uploaded images. Returns `202 Accepted` with the job row; the `id` is used for polling.

**Request**

```json
{
  "person_image_id": "5b3a4c6d-9e1f-4a2b-8c3d-7e0f1a2b3c4d",
  "fabric_image_id": "f9d8e7c6-b5a4-4932-81f0-e2d3c4b5a697",
  "garment_type": "shirt",
  "garment_style": "slim",
  "gender": "MEN"
}
```

`gender` is optional (`MEN` / `WOMEN` / `KIDS`).

**202 Accepted**

```json
{
  "id": "a1b2c3d4-e5f6-4789-9abc-def012345678",
  "user_id": "2a1f0d4b-7b2e-4f21-9c5e-3b81c6d9f20a",
  "person_image_id": "5b3a4c6d-9e1f-4a2b-8c3d-7e0f1a2b3c4d",
  "fabric_image_id": "f9d8e7c6-b5a4-4932-81f0-e2d3c4b5a697",
  "garment_type": "shirt",
  "garment_style": "slim",
  "gender": "MEN",
  "status": "QUEUED",
  "error_message": null,
  "result_url": null,
  "result_image_id": null,
  "created_at": "2026-09-01T10:00:00Z",
  "started_at": null,
  "completed_at": null
}
```

**Errors** - `400` if either image id does not belong to the user; this job is marked `FAILED` if the job broker is unreachable at enqueue time. In that case the response is still 202 but `status` will be `FAILED`.

---

## GET /try-on/{id}

Poll a job's status. Ownership is enforced; other users get `404`.

**200 OK** - while processing:

```json
{
  "id": "a1b2c3d4-e5f6-4789-9abc-def012345678",
  "status": "PROCESSING",
  "error_message": null,
  "result_url": null,
  "started_at": "2026-09-01T10:00:05Z"
}
```

**200 OK** - when done:

```json
{
  "id": "a1b2c3d4-e5f6-4789-9abc-def012345678",
  "status": "COMPLETED",
  "error_message": null,
  "result_url": "https://ik.imagekit.io/your-endpoint/vastrai/results/result-123.jpg",
  "result_image_id": "c7d8e9f0-a1b2-4c3d-8e5f-60718293a4b5",
  "started_at": "2026-09-01T10:00:05Z",
  "completed_at": "2026-09-01T10:00:35Z"
}
```

Honest statuses: `QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED` (with `error_message`).

**Errors** - `404` for unknown/malformed id or a job owned by another user.

---

## GET /try-on/{id}/result

Returns the result record once the job is `COMPLETED`.

**200 OK**

```json
{
  "id": "8e9f0a1b-2c3d-4e5f-8a9b-0c1d2e3f4051",
  "try_on_job_id": "a1b2c3d4-e5f6-4789-9abc-def012345678",
  "result_image_id": "c7d8e9f0-a1b2-4c3d-8e5f-60718293a4b5",
  "result_url": "https://ik.imagekit.io/your-endpoint/vastrai/results/result-123.jpg",
  "created_at": "2026-09-01T10:00:35Z"
}
```

**Errors** - `404` while the job is not yet `COMPLETED` (including `FAILED`), or the job does not exist.

---

## GET /health

**200 OK**

```json
{
  "status": "ok",
  "app": "VastrAI API"
}
```