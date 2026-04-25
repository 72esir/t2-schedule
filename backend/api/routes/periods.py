from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core import get_current_active_user
from backend.db import get_db
from backend.models import CollectionPeriod, ScheduleEntry, User, UserRole
from backend.schemas import CollectionPeriodCreate, CollectionPeriodOut

router = APIRouter(prefix="/periods", tags=["periods"])


@router.get("/current", response_model=Optional[CollectionPeriodOut])
def get_current_period(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if not current_user.alliance:
        return None

    return (
        db.query(CollectionPeriod)
        .filter(CollectionPeriod.is_open.is_(True), CollectionPeriod.alliance == current_user.alliance)
        .order_by(CollectionPeriod.created_at.desc())
        .first()
    )


@router.post("", response_model=CollectionPeriodOut, status_code=status.HTTP_201_CREATED)
def create_period(
    payload: CollectionPeriodCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    if not current_user.alliance:
        raise HTTPException(status_code=400, detail="У пользователя не указан альянс")

    db.query(CollectionPeriod).filter(
        CollectionPeriod.is_open.is_(True),
        CollectionPeriod.alliance == current_user.alliance,
    ).update({"is_open": False, "updated_at": datetime.now(timezone.utc)})

    period = CollectionPeriod(
        alliance=current_user.alliance,
        period_start=payload.period_start,
        period_end=payload.period_end,
        deadline=payload.deadline,
        is_open=True,
    )
    db.add(period)
    db.commit()
    db.refresh(period)
    return period


@router.post("/{period_id}/close", response_model=CollectionPeriodOut)
def close_period(
    period_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    period = db.query(CollectionPeriod).filter(CollectionPeriod.id == period_id).first()
    if not period:
        raise HTTPException(status_code=404, detail="Период не найден")

    if current_user.role == UserRole.MANAGER and period.alliance != current_user.alliance:
        raise HTTPException(status_code=403, detail="Нет доступа к этому периоду")

    period.is_open = False
    period.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(period)
    return period


@router.get("/current/stats")
def get_current_period_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    period = (
        db.query(CollectionPeriod)
        .filter(CollectionPeriod.is_open.is_(True), CollectionPeriod.alliance == current_user.alliance)
        .first()
    )
    if not period:
        return {"total_employees": 0, "submitted_count": 0, "pending_count": 0}

    total_employees = db.query(User).filter(
        User.is_verified.is_(True),
        User.alliance == current_user.alliance,
    ).count()

    submitted_count = (
        db.query(func.count(func.distinct(ScheduleEntry.user_id)))
        .filter(ScheduleEntry.period_id == period.id)
        .join(User)
        .filter(User.alliance == current_user.alliance)
        .scalar()
    )

    return {
        "total_employees": total_employees,
        "submitted_count": submitted_count,
        "pending_count": total_employees - submitted_count,
    }


@router.get("/current/submissions")
def get_current_period_submissions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    period = (
        db.query(CollectionPeriod)
        .filter(CollectionPeriod.is_open.is_(True), CollectionPeriod.alliance == current_user.alliance)
        .first()
    )
    if not period:
        return {"submitted": [], "pending": []}

    all_users = db.query(User).filter(
        User.is_verified.is_(True),
        User.alliance == current_user.alliance,
    ).all()

    submitted_ids = {
        row[0]
        for row in db.query(ScheduleEntry.user_id)
        .filter(ScheduleEntry.period_id == period.id)
        .distinct()
        .all()
    }

    submitted = []
    pending = []
    for user in all_users:
        user_data = {
            "id": user.id,
            "full_name": user.full_name or user.email,
            "email": user.email,
            "alliance": user.alliance,
        }
        if user.id in submitted_ids:
            submitted.append(user_data)
        else:
            pending.append(user_data)

    return {"submitted": submitted, "pending": pending}


@router.get("/history")
def get_periods_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    return (
        db.query(CollectionPeriod)
        .filter(CollectionPeriod.alliance == current_user.alliance)
        .order_by(CollectionPeriod.created_at.desc())
        .all()
    )

