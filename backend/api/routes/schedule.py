from datetime import date
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core import get_current_verified_user, require_role
from backend.db import get_db
from backend.models import CollectionPeriod, ScheduleEntry, User, UserRole
from backend.schemas import ScheduleBulkUpdate, ScheduleDayPayload, ScheduleForUser

router = APIRouter(prefix="/schedules", tags=["schedules"])


def get_current_period(db: Session) -> Optional[CollectionPeriod]:
    return db.query(CollectionPeriod).filter(CollectionPeriod.is_open.is_(True)).first()


@router.get("/me", response_model=Dict[date, ScheduleDayPayload])
def get_my_schedule(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    current_period = get_current_period(db)
    if not current_period:
        return {}

    entries: List[ScheduleEntry] = (
        db.query(ScheduleEntry)
        .filter(
            ScheduleEntry.user_id == current_user.id,
            ScheduleEntry.period_id == current_period.id,
        )
        .all()
    )
    return {entry.day: ScheduleDayPayload(status=entry.status, meta=entry.meta) for entry in entries}


@router.put("/me", response_model=Dict[date, ScheduleDayPayload])
def update_my_schedule(
    payload: ScheduleBulkUpdate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    current_period = get_current_period(db)
    if not current_period:
        raise HTTPException(status_code=400, detail="Нет активного периода сбора")

    for day in payload.days.keys():
        if day < current_period.period_start or day > current_period.period_end:
            raise HTTPException(status_code=400, detail=f"Дата {day} выходит за границы текущего периода")

    db.query(ScheduleEntry).filter(
        ScheduleEntry.user_id == current_user.id,
        ScheduleEntry.period_id == current_period.id,
    ).delete()

    for day, day_payload in payload.days.items():
        db.add(
            ScheduleEntry(
                user_id=current_user.id,
                period_id=current_period.id,
                day=day,
                status=day_payload.status,
                meta=day_payload.meta,
            )
        )

    db.commit()

    entries = db.query(ScheduleEntry).filter(
        ScheduleEntry.user_id == current_user.id,
        ScheduleEntry.period_id == current_period.id,
    ).all()
    return {entry.day: ScheduleDayPayload(status=entry.status, meta=entry.meta) for entry in entries}


@router.get("/by-user/{user_id}", response_model=ScheduleForUser)
def get_schedule_for_user(
    user_id: int,
    _: User = Depends(require_role(UserRole.MANAGER)),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    current_period = get_current_period(db)
    if not current_period:
        return ScheduleForUser(user=user, entries={}, vacation_work=None)

    entries: List[ScheduleEntry] = (
        db.query(ScheduleEntry)
        .filter(
            ScheduleEntry.user_id == user.id,
            ScheduleEntry.period_id == current_period.id,
        )
        .all()
    )
    schedule_map = {entry.day: ScheduleDayPayload(status=entry.status, meta=entry.meta) for entry in entries}

    return ScheduleForUser(user=user, entries=schedule_map, vacation_work=None)

