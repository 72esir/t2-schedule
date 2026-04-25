from datetime import date, datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from backend.core import get_current_verified_user, require_role
from backend.db import get_db
from backend.models import (
    CollectionPeriod,
    ScheduleChangeRequest,
    ScheduleChangeRequestStatus,
    ScheduleEntry,
    User,
    UserRole,
)
from backend.schemas import (
    MyScheduleState,
    ScheduleBulkUpdate,
    ScheduleChangeRequestCreate,
    ScheduleChangeRequestOut,
    ScheduleDayPayload,
    ScheduleForUser,
    ScheduleSummary,
    ScheduleValidationResult,
)
from backend.services import build_schedule_summary, build_schedule_validation

router = APIRouter(prefix="/schedules", tags=["schedules"])
schedule_day_payload_adapter = TypeAdapter(ScheduleDayPayload)


def _serialize_meta(meta):
    if meta is None:
        return None
    if hasattr(meta, "model_dump"):
        return meta.model_dump()
    return meta


def _deserialize_day_payload(status: str, meta):
    return schedule_day_payload_adapter.validate_python({"status": status, "meta": meta})


def _serialize_days(days: Dict[date, ScheduleDayPayload]) -> dict[str, dict]:
    return {
        day.isoformat(): {
            "status": day_payload.status,
            "meta": _serialize_meta(day_payload.meta),
        }
        for day, day_payload in days.items()
    }


def _deserialize_days(days: dict | None) -> Dict[date, ScheduleDayPayload]:
    if not days:
        return {}
    return {
        date.fromisoformat(day_str): _deserialize_day_payload(payload["status"], payload.get("meta"))
        for day_str, payload in days.items()
    }


def _change_request_to_response(change_request: ScheduleChangeRequest) -> ScheduleChangeRequestOut:
    return ScheduleChangeRequestOut(
        id=change_request.id,
        user_id=change_request.user_id,
        period_id=change_request.period_id,
        status=change_request.status,
        employee_comment=change_request.employee_comment,
        manager_comment=change_request.manager_comment,
        proposed_days=_deserialize_days(change_request.proposed_schedule),
        created_at=change_request.created_at,
        resolved_at=change_request.resolved_at,
        resolved_by_manager_id=change_request.resolved_by_manager_id,
    )


def get_current_period(db: Session, alliance: Optional[str]) -> Optional[CollectionPeriod]:
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


def _validate_days_in_period(days: Dict[date, ScheduleDayPayload], period: CollectionPeriod) -> None:
    for day in days.keys():
        if day < period.period_start or day > period.period_end:
            raise HTTPException(
                status_code=400,
                detail=f"Р”Р°С‚Р° {day} РІС‹С…РѕРґРёС‚ Р·Р° РіСЂР°РЅРёС†С‹ С‚РµРєСѓС‰РµРіРѕ РїРµСЂРёРѕРґР°",
            )


def _replace_schedule_entries(
    *,
    db: Session,
    user_id: int,
    period_id: int,
    days: Dict[date, ScheduleDayPayload],
) -> None:
    db.query(ScheduleEntry).filter(
        ScheduleEntry.user_id == user_id,
        ScheduleEntry.period_id == period_id,
    ).delete()

    for day, day_payload in days.items():
        db.add(
            ScheduleEntry(
                user_id=user_id,
                period_id=period_id,
                day=day,
                status=day_payload.status,
                meta=_serialize_meta(day_payload.meta),
            )
        )


def _build_schedule_state(entries: List[ScheduleEntry]) -> MyScheduleState:
    if not entries:
        return MyScheduleState(days={}, last_saved_at=None)

    last_saved_at = max(entry.updated_at or entry.created_at for entry in entries)
    return MyScheduleState(
        days={entry.day: _deserialize_day_payload(entry.status, entry.meta) for entry in entries},
        last_saved_at=last_saved_at,
    )


@router.get("/me", response_model=Dict[date, ScheduleDayPayload])
def get_my_schedule(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    current_period = get_current_period(db, current_user.alliance)
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
    return {entry.day: _deserialize_day_payload(entry.status, entry.meta) for entry in entries}


@router.get("/me/state", response_model=MyScheduleState)
def get_my_schedule_state(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    current_period = get_current_period(db, current_user.alliance)
    if not current_period:
        return MyScheduleState(days={}, last_saved_at=None)

    entries: List[ScheduleEntry] = (
        db.query(ScheduleEntry)
        .filter(
            ScheduleEntry.user_id == current_user.id,
            ScheduleEntry.period_id == current_period.id,
        )
        .all()
    )
    return _build_schedule_state(entries)


@router.put("/me", response_model=Dict[date, ScheduleDayPayload])
def update_my_schedule(
    payload: ScheduleBulkUpdate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    current_period = get_current_period(db, current_user.alliance)
    if not current_period:
        raise HTTPException(status_code=400, detail="РќРµС‚ Р°РєС‚РёРІРЅРѕРіРѕ РїРµСЂРёРѕРґР° СЃР±РѕСЂР°")

    now = datetime.now(timezone.utc)
    if current_period.deadline < now:
        raise HTTPException(status_code=403, detail="РЎСЂРѕРє СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ СЂР°СЃРїРёСЃР°РЅРёСЏ РёСЃС‚РµРє")

    _validate_days_in_period(payload.days, current_period)
    _replace_schedule_entries(
        db=db,
        user_id=current_user.id,
        period_id=current_period.id,
        days=payload.days,
    )
    db.commit()

    entries = db.query(ScheduleEntry).filter(
        ScheduleEntry.user_id == current_user.id,
        ScheduleEntry.period_id == current_period.id,
    ).all()
    return {entry.day: _deserialize_day_payload(entry.status, entry.meta) for entry in entries}


@router.post("/change-request", response_model=ScheduleChangeRequestOut)
def create_schedule_change_request(
    payload: ScheduleChangeRequestCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    current_period = get_current_period(db, current_user.alliance)
    if not current_period:
        raise HTTPException(status_code=400, detail="РќРµС‚ Р°РєС‚РёРІРЅРѕРіРѕ РїРµСЂРёРѕРґР° СЃР±РѕСЂР°")

    now = datetime.now(timezone.utc)
    if current_period.deadline >= now:
        raise HTTPException(status_code=400, detail="Р—Р°СЏРІРєР° РЅР° РїРµСЂРµСЃРјРѕС‚СЂ РґРѕСЃС‚СѓРїРЅР° С‚РѕР»СЊРєРѕ РїРѕСЃР»Рµ РґРµРґР»Р°Р№РЅР°")

    _validate_days_in_period(payload.days, current_period)

    existing_request = (
        db.query(ScheduleChangeRequest)
        .filter(
            ScheduleChangeRequest.user_id == current_user.id,
            ScheduleChangeRequest.period_id == current_period.id,
        )
        .first()
    )
    if existing_request:
        raise HTTPException(status_code=400, detail="Р—Р°СЏРІРєР° РЅР° РїРµСЂРµСЃРјРѕС‚СЂ СѓР¶Рµ Р±С‹Р»Р° РїРѕРґР°РЅР° РІ СЌС‚РѕРј РїРµСЂРёРѕРґРµ")

    change_request = ScheduleChangeRequest(
        user_id=current_user.id,
        period_id=current_period.id,
        status=ScheduleChangeRequestStatus.PENDING,
        employee_comment=payload.employee_comment,
        proposed_schedule=_serialize_days(payload.days),
    )
    db.add(change_request)
    db.commit()
    db.refresh(change_request)
    return _change_request_to_response(change_request)


@router.get("/change-request/me", response_model=Optional[ScheduleChangeRequestOut])
def get_my_schedule_change_request(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    current_period = get_current_period(db, current_user.alliance)
    if not current_period:
        return None

    change_request = (
        db.query(ScheduleChangeRequest)
        .filter(
            ScheduleChangeRequest.user_id == current_user.id,
            ScheduleChangeRequest.period_id == current_period.id,
        )
        .first()
    )
    if not change_request:
        return None

    return _change_request_to_response(change_request)


@router.get("/me/summary", response_model=ScheduleSummary)
def get_my_schedule_summary(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    current_period = get_current_period(db, current_user.alliance)
    if not current_period:
        return ScheduleSummary(
            daily_hours={},
            weekly_hours={},
            period_total_hours=0,
            vacation_days_count=0,
            max_work_streak=0,
        )

    entries = db.query(ScheduleEntry).filter(
        ScheduleEntry.user_id == current_user.id,
        ScheduleEntry.period_id == current_period.id,
    ).all()
    return ScheduleSummary(**build_schedule_summary(entries))


@router.get("/by-user/{user_id}", response_model=ScheduleForUser)
def get_schedule_for_user(
    user_id: int,
    current_user: User = Depends(require_role(UserRole.MANAGER)),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ РЅРµ РЅР°Р№РґРµРЅ")

    if user.alliance != current_user.alliance:
        raise HTTPException(status_code=403, detail="РќРµС‚ РґРѕСЃС‚СѓРїР° Рє СЃРѕС‚СЂСѓРґРЅРёРєСѓ РёР· РґСЂСѓРіРѕРіРѕ Р°Р»СЊСЏРЅСЃР°")

    current_period = get_current_period(db, user.alliance)
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
    schedule_map = {entry.day: _deserialize_day_payload(entry.status, entry.meta) for entry in entries}

    return ScheduleForUser(user=user, entries=schedule_map, vacation_work=None)


@router.get("/by-user/{user_id}/summary", response_model=ScheduleSummary)
def get_schedule_summary_for_user(
    user_id: int,
    current_user: User = Depends(require_role(UserRole.MANAGER)),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ РЅРµ РЅР°Р№РґРµРЅ")

    if user.alliance != current_user.alliance:
        raise HTTPException(status_code=403, detail="РќРµС‚ РґРѕСЃС‚СѓРїР° Рє СЃРѕС‚СЂСѓРґРЅРёРєСѓ РёР· РґСЂСѓРіРѕРіРѕ Р°Р»СЊСЏРЅСЃР°")

    current_period = get_current_period(db, user.alliance)
    if not current_period:
        return ScheduleSummary(
            daily_hours={},
            weekly_hours={},
            period_total_hours=0,
            vacation_days_count=0,
            max_work_streak=0,
        )

    entries = db.query(ScheduleEntry).filter(
        ScheduleEntry.user_id == user.id,
        ScheduleEntry.period_id == current_period.id,
    ).all()
    return ScheduleSummary(**build_schedule_summary(entries))


@router.get("/me/validation", response_model=ScheduleValidationResult)
def get_my_schedule_validation(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    current_period = get_current_period(db, current_user.alliance)
    if not current_period:
        empty_summary = ScheduleSummary(
            daily_hours={},
            weekly_hours={},
            period_total_hours=0,
            vacation_days_count=0,
            max_work_streak=0,
        )
        return ScheduleValidationResult(is_valid=True, violations=[], summary=empty_summary)

    entries = db.query(ScheduleEntry).filter(
        ScheduleEntry.user_id == current_user.id,
        ScheduleEntry.period_id == current_period.id,
    ).all()
    return ScheduleValidationResult(**build_schedule_validation(entries))


@router.get("/by-user/{user_id}/validation", response_model=ScheduleValidationResult)
def get_schedule_validation_for_user(
    user_id: int,
    current_user: User = Depends(require_role(UserRole.MANAGER)),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ РЅРµ РЅР°Р№РґРµРЅ")

    if user.alliance != current_user.alliance:
        raise HTTPException(status_code=403, detail="РќРµС‚ РґРѕСЃС‚СѓРїР° Рє СЃРѕС‚СЂСѓРґРЅРёРєСѓ РёР· РґСЂСѓРіРѕРіРѕ Р°Р»СЊСЏРЅСЃР°")

    current_period = get_current_period(db, user.alliance)
    if not current_period:
        empty_summary = ScheduleSummary(
            daily_hours={},
            weekly_hours={},
            period_total_hours=0,
            vacation_days_count=0,
            max_work_streak=0,
        )
        return ScheduleValidationResult(is_valid=True, violations=[], summary=empty_summary)

    entries = db.query(ScheduleEntry).filter(
        ScheduleEntry.user_id == user.id,
        ScheduleEntry.period_id == current_period.id,
    ).all()
    return ScheduleValidationResult(**build_schedule_validation(entries))
