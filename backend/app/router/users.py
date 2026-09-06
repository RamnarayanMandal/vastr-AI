from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import CreditBalance, CreditTransaction, MediaAsset, Notification, PasswordResetToken, TryOnJob, TryOnResult, User

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/me/deactivate")
def deactivate(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.status = "DEACTIVATED"
    db.commit()
    return {"status": "DEACTIVATED"}


@router.delete("/me")
def delete_account(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.query(Notification).filter(Notification.user_id == user.id).delete(synchronize_session=False)
    db.query(CreditTransaction).filter(CreditTransaction.user_id == user.id).delete(synchronize_session=False)
    db.query(CreditBalance).filter(CreditBalance.user_id == user.id).delete(synchronize_session=False)
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete(synchronize_session=False)
    jobs = db.query(TryOnJob).filter(TryOnJob.user_id == user.id).all()
    job_ids = [job.id for job in jobs]
    if job_ids:
        result_asset_ids = [row[0] for row in db.query(TryOnResult.result_image_id).filter(TryOnResult.try_on_job_id.in_(job_ids)).all()]
        db.query(TryOnResult).filter(TryOnResult.try_on_job_id.in_(job_ids)).delete(synchronize_session=False)
        db.query(TryOnJob).filter(TryOnJob.id.in_(job_ids)).delete(synchronize_session=False)
        if result_asset_ids:
            db.query(MediaAsset).filter(MediaAsset.id.in_(result_asset_ids)).delete(synchronize_session=False)
    db.query(MediaAsset).filter(MediaAsset.user_id == user.id).delete(synchronize_session=False)
    db.delete(user)
    db.commit()
    return {"deleted": True}