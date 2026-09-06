from datetime import datetime
from uuid import uuid4

from passlib.context import CryptContext
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


def gen_uuid():
    return uuid4()


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    full_name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    mobile = Column(String(20), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), nullable=False, default="ACTIVE", server_default="ACTIVE")

    jobs = relationship("TryOnJob", back_populates="user")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    credit_balance = relationship("CreditBalance", back_populates="user", uselist=False, cascade="all, delete-orphan")
    credit_transactions = relationship("CreditTransaction", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.hashed_password = pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.hashed_password)


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    kind = Column(String(20), nullable=False)  # person | fabric | result
    imagekit_file_id = Column(String(120), nullable=False)
    url = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class TryOnJob(Base):
    __tablename__ = "try_on_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    person_image_id = Column(UUID(as_uuid=True), ForeignKey("media_assets.id"), nullable=False)
    fabric_image_id = Column(UUID(as_uuid=True), ForeignKey("media_assets.id"), nullable=False)
    garment_type = Column(String(60), nullable=False)
    garment_style = Column(String(60), nullable=False)
    gender = Column(String(10), nullable=True)
    status = Column(String(20), default="QUEUED", nullable=False, index=True)
    provider = Column(String(60), nullable=True)
    model_version = Column(String(120), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=2)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="jobs")
    result = relationship(
        "TryOnResult", back_populates="job", uselist=False, cascade="all, delete-orphan"
    )


class TryOnResult(Base):
    __tablename__ = "try_on_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    try_on_job_id = Column(UUID(as_uuid=True), ForeignKey("try_on_jobs.id"), nullable=False, index=True)
    result_image_id = Column(UUID(as_uuid=True), ForeignKey("media_assets.id"), nullable=False)
    result_url = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("TryOnJob", back_populates="result")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(40), nullable=False)
    is_read = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="notifications")


class CreditBalance(Base):
    __tablename__ = "credit_balances"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    available = Column(Integer, nullable=False, default=0, server_default="0")
    total_used = Column(Integer, nullable=False, default=0, server_default="0")
    total_added = Column(Integer, nullable=False, default=0, server_default="0")
    user = relationship("User", back_populates="credit_balance")


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(20), nullable=False)
    amount = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    reference_id = Column(String(120), nullable=True)
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="credit_transactions")