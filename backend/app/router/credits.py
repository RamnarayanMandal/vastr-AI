from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import CreditBalance, CreditTransaction, User
from ..schemas import CreditTransactionOut, CreditsOut

router = APIRouter(prefix="/credits", tags=["credits"])


def _balance(db: Session, user: User) -> CreditBalance:
    balance = db.query(CreditBalance).filter(CreditBalance.user_id == user.id).first()
    if balance is None:
        balance = CreditBalance(user_id=user.id)
        db.add(balance)
        db.commit()
        db.refresh(balance)
    return balance


@router.get("", response_model=CreditsOut)
def get_credits(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    balance = _balance(db, user)
    transactions = db.query(CreditTransaction).filter(CreditTransaction.user_id == user.id).order_by(CreditTransaction.created_at.desc()).limit(100).all()
    return CreditsOut(balance=balance.available, total_used=balance.total_used, total_added=balance.total_added, transactions=transactions)


@router.get("/history", response_model=list[CreditTransactionOut])
def credit_history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(CreditTransaction).filter(CreditTransaction.user_id == user.id).order_by(CreditTransaction.created_at.desc()).all()