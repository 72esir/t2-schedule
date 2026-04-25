from collections import defaultdict
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core import get_current_active_user
from backend.db import get_db
from backend.models import CollectionPeriod, ScheduleEntry, User, UserRole, VacationDaysStatus
from backend.schemas import (
    ManagerDashboardOut,
    ManagerProblemEmployeeOut,
    UserOut,
    VacationDaysModerationRequest,
)
from backend.services import build_schedule_validation

router = APIRouter(prefix="/manager", tags=["manager"])


def require_manager(current_user: User = Depends(get_current_active_user)):
    if current_user.role != UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="РўСЂРµР±СѓСЋС‚СЃСЏ РїСЂР°РІР° РјРµРЅРµРґР¶РµСЂР°")
    return current_user


@router.get("/dashboard", response_model=ManagerDashboardOut)
def get_manager_dashboard(
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    alliance_users_query = db.query(User).filter(
        User.alliance == current_user.alliance,
        User.role == UserRole.USER,
    )

    verified_users = alliance_users_query.filter(User.is_verified.is_(True)).all()
    total_employees = len(verified_users)

    pending_verification_count = alliance_users_query.filter(User.is_verified.is_(False)).count()
    pending_vacation_moderation_count = alliance_users_query.filter(
        User.vacation_days_status == VacationDaysStatus.PENDING,
        User.vacation_days_declared.is_not(None),
    ).count()

    period = (
        db.query(CollectionPeriod)
        .filter(CollectionPeriod.is_open.is_(True), CollectionPeriod.alliance == current_user.alliance)
        .order_by(CollectionPeriod.created_at.desc())
        .first()
    )
    if not period:
        return ManagerDashboardOut(
            current_period=None,
            total_employees=total_employees,
            submitted_count=0,
            pending_count=total_employees,
            pending_verification_count=pending_verification_count,
            pending_vacation_moderation_count=pending_vacation_moderation_count,
            employees_with_violations_count=0,
            problem_employees=[],
        )

    submitted_count = (
        db.query(func.count(func.distinct(ScheduleEntry.user_id)))
        .filter(ScheduleEntry.period_id == period.id)
        .join(User)
        .filter(User.alliance == current_user.alliance, User.role == UserRole.USER)
        .scalar()
    ) or 0

    entries = (
        db.query(ScheduleEntry)
        .join(User)
        .filter(
            ScheduleEntry.period_id == period.id,
            User.alliance == current_user.alliance,
            User.role == UserRole.USER,
        )
        .all()
    )

    user_map = {user.id: user for user in verified_users}
    entries_by_user: dict[int, list[ScheduleEntry]] = defaultdict(list)
    for entry in entries:
        entries_by_user[entry.user_id].append(entry)

    problem_employees: list[ManagerProblemEmployeeOut] = []
    for user_id, user_entries in entries_by_user.items():
        validation = build_schedule_validation(user_entries)
        if not validation["violations"]:
            continue

        user = user_map.get(user_id)
        if not user:
            continue

        problem_employees.append(
            ManagerProblemEmployeeOut(
                user_id=user.id,
                full_name=user.full_name or user.email or f"User {user.id}",
                email=user.email,
                violation_count=len(validation["violations"]),
                violation_codes=[violation["code"] for violation in validation["violations"]],
                summary=validation["summary"],
            )
        )

    problem_employees.sort(key=lambda item: (-item.violation_count, item.full_name.lower()))

    return ManagerDashboardOut(
        current_period=period,
        total_employees=total_employees,
        submitted_count=submitted_count,
        pending_count=max(total_employees - submitted_count, 0),
        pending_verification_count=pending_verification_count,
        pending_vacation_moderation_count=pending_vacation_moderation_count,
        employees_with_violations_count=len(problem_employees),
        problem_employees=problem_employees,
    )


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
        raise HTTPException(status_code=404, detail="РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ РЅРµ РЅР°Р№РґРµРЅ")
    if user.alliance != current_user.alliance:
        raise HTTPException(status_code=403, detail="РќРµС‚ РґРѕСЃС‚СѓРїР° Рє СЃРѕС‚СЂСѓРґРЅРёРєСѓ РёР· РґСЂСѓРіРѕРіРѕ Р°Р»СЊСЏРЅСЃР°")
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
        raise HTTPException(status_code=404, detail="РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ РЅРµ РЅР°Р№РґРµРЅ")
    if user.alliance != current_user.alliance:
        raise HTTPException(status_code=403, detail="РќРµС‚ РґРѕСЃС‚СѓРїР° Рє СЃРѕС‚СЂСѓРґРЅРёРєСѓ РёР· РґСЂСѓРіРѕРіРѕ Р°Р»СЊСЏРЅСЃР°")

    if payload.status == VacationDaysStatus.REJECTED:
        user.vacation_days_approved = None
    else:
        user.vacation_days_approved = payload.approved_days

    user.vacation_days_status = payload.status
    db.commit()
    db.refresh(user)
    return user
