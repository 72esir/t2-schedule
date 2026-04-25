from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core import get_current_verified_user
from backend.db import get_db
from backend.models import CollectionPeriod, ScheduleEntry, ScheduleTemplate, User
from backend.schemas import ScheduleTemplateCreate, ScheduleTemplateOut, SuggestedTemplateOut
from backend.services import build_suggested_template_for_current_period

router = APIRouter(prefix="/templates", tags=["templates"])


def get_current_period(db: Session, alliance: str | None) -> CollectionPeriod | None:
    if not alliance:
        return None

    return (
        db.query(CollectionPeriod)
        .filter(
            CollectionPeriod.is_open.is_(True),
            CollectionPeriod.alliance == alliance,
        )
        .order_by(CollectionPeriod.created_at.desc())
        .first()
    )


@router.get("", response_model=List[ScheduleTemplateOut])
def get_my_templates(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(ScheduleTemplate)
        .filter(ScheduleTemplate.user_id == current_user.id)
        .order_by(ScheduleTemplate.created_at.desc())
        .all()
    )


@router.get("/suggested/current", response_model=SuggestedTemplateOut)
def get_suggested_template_for_current_period(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    current_period = get_current_period(db, current_user.alliance)
    return SuggestedTemplateOut(
        **build_suggested_template_for_current_period(
            db,
            user=current_user,
            current_period=current_period,
        )
    )


@router.post("/suggested/current/apply", response_model=SuggestedTemplateOut)
def apply_suggested_template_for_current_period(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    current_period = get_current_period(db, current_user.alliance)
    if not current_period:
        raise HTTPException(status_code=400, detail="No active period")

    if current_period.deadline < datetime.now(timezone.utc):
        raise HTTPException(status_code=403, detail="Schedule editing deadline has passed")

    suggestion = build_suggested_template_for_current_period(
        db,
        user=current_user,
        current_period=current_period,
    )
    if not suggestion["has_suggestion"]:
        raise HTTPException(status_code=404, detail="No suggested template available")

    db.query(ScheduleEntry).filter(
        ScheduleEntry.user_id == current_user.id,
        ScheduleEntry.period_id == current_period.id,
    ).delete()

    for day, payload in suggestion["days"].items():
        db.add(
            ScheduleEntry(
                user_id=current_user.id,
                period_id=current_period.id,
                day=day,
                status=payload["status"],
                meta=payload.get("meta"),
            )
        )

    db.commit()
    return SuggestedTemplateOut(**suggestion)


@router.post("", response_model=ScheduleTemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: ScheduleTemplateCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    template = ScheduleTemplate(
        user_id=current_user.id,
        name=payload.name,
        work_days=payload.work_days,
        rest_days=payload.rest_days,
        shift_start=payload.shift_start,
        shift_end=payload.shift_end,
        has_break=payload.has_break,
        break_start=payload.break_start,
        break_end=payload.break_end,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    template = db.query(ScheduleTemplate).filter(
        ScheduleTemplate.id == template_id,
        ScheduleTemplate.user_id == current_user.id,
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")

    db.delete(template)
    db.commit()
    return None

