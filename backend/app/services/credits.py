from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..config import settings
from ..models import CreditBalance, CreditTransaction


def reserve_try_on_credit(db: Session, user_id, reference_id: str) -> None:
    cost = settings.try_on_credit_cost
    balance = (
        db.query(CreditBalance)
        .filter(CreditBalance.user_id == user_id)
        .with_for_update()
        .first()
    )
    if balance is None:
        balance = CreditBalance(
            user_id=user_id,
            available=settings.initial_ai_credits,
            total_used=0,
            total_added=settings.initial_ai_credits,
        )
        db.add(balance)
        db.flush()
    if balance.available < cost:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"code": "INSUFFICIENT_CREDITS", "message": "You do not have enough AI credits."},
        )
    balance.available -= cost
    balance.total_used += cost
    db.add(CreditTransaction(
        user_id=user_id,
        type="USAGE",
        amount=-cost,
        balance_after=balance.available,
        reference_id=reference_id,
        description="AI Try-On",
    ))