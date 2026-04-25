from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core import get_current_active_user
from backend.db import get_db
from backend.models import User, UserRole, VacationDaysStatus
from backend.schemas import UserOut, VacationDaysModerationRequest

router = APIRouter(prefix="/manager", tags=["manager"])


def require_manager(current_user: User = Depends(get_current_active_user)):
    if current_user.role != UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Требуются права менеджера")
    return current_user


@router.get("/vacation-days/pending", response_model=List[UserOut])
def get_pending_vacation_days(
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    return (
        db.query(User)
        .filter(
            User.alliance == current_user.alliance,
            User.role == UserRole.USER,
            User.vacation_days_status == VacationDaysStatus.PENDING,
            User.vacation_days_declared.is_not(None),
        )
        .order_by(User.created_at.desc())
        .all()
    )


@router.get("/users/pending-verification", response_model=List[UserOut])
def get_pending_verification_users(
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    return (
        db.query(User)
        .filter(
            User.alliance == current_user.alliance,
            User.role == UserRole.USER,
            User.is_verified.is_(False),
        )
        .order_by(User.created_at.desc())
        .all()
    )


@router.get("/users", response_model=List[UserOut])
def get_users(
    verified: Optional[bool] = None,
    alliance: Optional[str] = None,
    role: Optional[UserRole] = None,
    vacation_days_status: Optional[VacationDaysStatus] = None,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    alliance = alliance or current_user.alliance
    query = query.filter(User.alliance == alliance)

    if verified is not None:
        query = query.filter(User.is_verified == verified)
    if role:
        query = query.filter(User.role == role)
    if vacation_days_status:
        query = query.filter(User.vacation_days_status == vacation_days_status)

    return query.all()


@router.put("/users/{user_id}/verify", response_model=UserOut)
def verify_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if user.alliance != current_user.alliance:
        raise HTTPException(status_code=403, detail="Нет доступа к сотруднику из другого альянса")
    user.is_verified = True
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}/vacation-days", response_model=UserOut)
def moderate_vacation_days(
    user_id: int,
    payload: VacationDaysModerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if user.alliance != current_user.alliance:
        raise HTTPException(status_code=403, detail="Нет доступа к сотруднику из другого альянса")

    if payload.status == VacationDaysStatus.REJECTED:
        user.vacation_days_approved = None
    else:
        user.vacation_days_approved = payload.approved_days

    user.vacation_days_status = payload.status
    db.commit()
    db.refresh(user)
    return user
