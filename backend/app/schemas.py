import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

JobStatus = Literal["QUEUED", "PROCESSING", "COMPLETED", "FAILED"]


# ---------- Auth ----------
class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    mobile: str = Field(min_length=8, max_length=20)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    identifier: str
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    mobile: str
    status: str = "ACTIVE"

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Uploads ----------
class UploadResponse(BaseModel):
    image_id: uuid.UUID
    url: str


# ---------- Try-On ----------
class TryOnCreate(BaseModel):
    person_image_id: uuid.UUID
    fabric_image_id: uuid.UUID
    garment_type: str = Field(min_length=1, max_length=60)
    garment_style: str = Field(min_length=1, max_length=60)
    gender: Optional[str] = Field(default=None, max_length=10)


class TryOnJobOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    person_image_id: uuid.UUID
    fabric_image_id: uuid.UUID
    garment_type: str
    garment_style: str
    gender: Optional[str]
    status: JobStatus
    error_message: Optional[str]
    provider: Optional[str] = None
    model_version: Optional[str] = None
    result_url: Optional[str] = None
    result_image_id: Optional[uuid.UUID] = None
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class TryOnResultOut(BaseModel):
    id: uuid.UUID
    try_on_job_id: uuid.UUID
    result_image_id: uuid.UUID
    result_url: str
    created_at: datetime

    model_config = {"from_attributes": True}


class HistoryItemOut(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    person_image_url: Optional[str]
    fabric_image_url: Optional[str]
    result_url: str
    garment_type: str
    garment_style: str
    gender: Optional[str]
    created_at: datetime


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    otp: str = Field(pattern=r"^\d{6}$")
    new_password: str = Field(min_length=8, max_length=128)


class NotificationOut(BaseModel):
    id: uuid.UUID
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class CreditTransactionOut(BaseModel):
    id: uuid.UUID
    type: str
    amount: int
    balance_after: int
    reference_id: Optional[str]
    description: str
    created_at: datetime
    model_config = {"from_attributes": True}


class CreditsOut(BaseModel):
    balance: int
    total_used: int
    total_added: int
    transactions: list[CreditTransactionOut] = []