from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core import get_current_active_user
from backend.db import get_db
from backend.models import CollectionPeriod, ScheduleEntry, User, UserRole
from backend.schemas import (
    CollectionPeriodCreate,
    CollectionPeriodFromTemplateCreate,
    CollectionPeriodOut,
    PeriodTemplateOut,
)

router = APIRouter(prefix="/periods", tags=["periods"])

PERIOD_TEMPLATES = [
    PeriodTemplateOut(
        type="week",
        label="1 week",
        description="Creates a 7-day period starting from period_start.",
        requires_period_end=False,
    ),
    PeriodTemplateOut(
        type="two_weeks",
        label="2 weeks",
        description="Creates a 14-day period starting from period_start.",
        requires_period_end=False,
    ),
    PeriodTemplateOut(
        type="month",
        label="Calendar month",
        description="Creates a period from period_start to the last day of that month.",
        requires_period_end=False,
    ),
    PeriodTemplateOut(
        type="custom",
        label="Custom range",
        description="Creates a period using explicit period_start and period_end.",
        requires_period_end=True,
    ),
]


def require_manager(user: User) -> None:
    if user.role != UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="РўСЂРµР±СѓСЋС‚СЃСЏ РїСЂР°РІР° РјРµРЅРµРґР¶РµСЂР°")


def create_alliance_period(
    *,
    db: Session,
    alliance: str,
    period_start,
    period_end,
    deadline,
) -> CollectionPeriod:
    db.query(CollectionPeriod).filter(
        CollectionPeriod.is_open.is_(True),
        CollectionPeriod.alliance == alliance,
    ).update({"is_open": False, "updated_at": datetime.now(timezone.utc)})

    period = CollectionPeriod(
        alliance=alliance,
        period_start=period_start,
        period_end=period_end,
        deadline=deadline,
        is_open=True,
    )
    db.add(period)
    db.commit()
    db.refresh(period)
    return period


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


@router.get("/templates", response_model=list[PeriodTemplateOut])
def get_period_templates(
    current_user: User = Depends(get_current_active_user),
):
    require_manager(current_user)
    return PERIOD_TEMPLATES


@router.post("", response_model=CollectionPeriodOut, status_code=status.HTTP_201_CREATED)
def create_period(
    payload: CollectionPeriodCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    require_manager(current_user)

    if not current_user.alliance:
        raise HTTPException(status_code=400, detail="РЈ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ РЅРµ СѓРєР°Р·Р°РЅ Р°Р»СЊСЏРЅСЃ")

    return create_alliance_period(
        db=db,
        alliance=current_user.alliance,
        period_start=payload.period_start,
        period_end=payload.period_end,
        deadline=payload.deadline,
    )


@router.post("/from-template", response_model=CollectionPeriodOut, status_code=status.HTTP_201_CREATED)
def create_period_from_template(
    payload: CollectionPeriodFromTemplateCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    require_manager(current_user)

    if not current_user.alliance:
        raise HTTPException(status_code=400, detail="РЈ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ РЅРµ СѓРєР°Р·Р°РЅ Р°Р»СЊСЏРЅСЃ")

    return create_alliance_period(
        db=db,
        alliance=current_user.alliance,
        period_start=payload.period_start,
        period_end=payload.resolve_period_end(),
        deadline=payload.deadline,
    )


@router.post("/{period_id}/close", response_model=CollectionPeriodOut)
def close_period(
    period_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    require_manager(current_user)

    period = db.query(CollectionPeriod).filter(CollectionPeriod.id == period_id).first()
    if not period:
        raise HTTPException(status_code=404, detail="РџРµСЂРёРѕРґ РЅРµ РЅР°Р№РґРµРЅ")
    if period.alliance != current_user.alliance:
        raise HTTPException(status_code=403, detail="РќРµС‚ РґРѕСЃС‚СѓРїР° Рє СЌС‚РѕРјСѓ РїРµСЂРёРѕРґСѓ")

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
    require_manager(current_user)

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
    require_manager(current_user)

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
    require_manager(current_user)

    return (
        db.query(CollectionPeriod)
        .filter(CollectionPeriod.alliance == current_user.alliance)
        .order_by(CollectionPeriod.created_at.desc())
        .all()
    )
