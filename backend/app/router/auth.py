import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import CreditBalance, PasswordResetToken, User
from ..schemas import AuthResponse, ForgotPasswordRequest, LoginRequest, RegisterRequest, ResetPasswordRequest, UserOut
from ..security import create_access_token
from ..services.email import email_service
from ..config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


def _build_auth_response(user: User) -> AuthResponse:
    token = create_access_token(str(user.id))
    return AuthResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = (
        db.query(User)
        .filter((User.email == payload.email) | (User.mobile == payload.mobile))
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email or mobile already exists.",
        )
    user = User(
        full_name=payload.full_name,
        email=payload.email.lower(),
        mobile=payload.mobile,
    )
    user.set_password(payload.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(CreditBalance(user_id=user.id, available=settings.initial_ai_credits, total_added=settings.initial_ai_credits))
    db.commit()
    return _build_auth_response(user)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter((User.email == payload.identifier.lower()) | (User.mobile == payload.identifier))
        .first()
    )
    if user is None or not user.verify_password(payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/mobile or password.",
        )
    if user.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "ACCOUNT_DEACTIVATED", "message": "Account is deactivated."})
    return _build_auth_response(user)


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)):
    return UserOut.model_validate(current)


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user:
        raw = f"{secrets.randbelow(1_000_000):06d}"
        token = PasswordResetToken(
            user_id=user.id,
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            expires_at=datetime.utcnow() + timedelta(minutes=10),
        )
        db.add(token)
        db.commit()
        email_service.send_password_reset_email(
            user.email,
            raw,
        )
    return {"message": "If the email is registered, a password reset OTP has been sent."}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(payload.otp.encode()).hexdigest()
    record = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()
    if record is None or record.used_at is not None:
        raise HTTPException(status_code=400, detail={"code": "RESET_TOKEN_INVALID", "message": "Reset token is invalid."})
    if record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail={"code": "RESET_TOKEN_EXPIRED", "message": "Reset token has expired."})
    user = db.query(User).filter(User.id == record.user_id).first()
    if user is None:
        raise HTTPException(status_code=400, detail={"code": "RESET_TOKEN_INVALID", "message": "Reset token is invalid."})
    user.set_password(payload.new_password)
    record.used_at = datetime.utcnow()
    db.commit()
    return {"message": "Password changed successfully."}