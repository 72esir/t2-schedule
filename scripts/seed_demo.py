from __future__ import annotations

import sys
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.auth import get_password_hash
from backend.db import SessionLocal
from backend.models import (
    CollectionPeriod,
    ScheduleChangeRequest,
    ScheduleChangeRequestStatus,
    ScheduleEntry,
    ScheduleTemplate,
    User,
    UserRole,
    VacationDaysStatus,
    VerificationToken,
)

DEMO_ALLIANCE = "Demo Alliance"
MANAGER_EMAIL = "manager@company.ru"
EMPLOYEE_PASSWORD = "Employee123!"
MANAGER_PASSWORD = "Manager123!"


def log(message: str) -> None:
    print(f"[seed] {message}")


def next_monday(day: date) -> date:
    days_ahead = (7 - day.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return day + timedelta(days=days_ahead)


def schedule_shift(start: str, end: str) -> dict:
    return {
        "status": "shift",
        "meta": {
            "shiftStart": start,
            "shiftEnd": end,
        },
    }


def cleanup_demo_data(session) -> None:
    demo_emails = [
        MANAGER_EMAIL,
        "employee1@company.ru",
        "employee2@company.ru",
        "employee3@company.ru",
        "employee4@company.ru",
        "employee5@company.ru",
    ]

    users = session.query(User).filter(User.email.in_(demo_emails)).all()
    user_ids = [user.id for user in users]
    period_ids = [
        period_id
        for (period_id,) in session.query(CollectionPeriod.id)
        .filter(CollectionPeriod.alliance == DEMO_ALLIANCE)
        .all()
    ]

    if user_ids:
        session.query(ScheduleEntry).filter(ScheduleEntry.user_id.in_(user_ids)).delete(
            synchronize_session=False
        )
        session.query(ScheduleTemplate).filter(ScheduleTemplate.user_id.in_(user_ids)).delete(
            synchronize_session=False
        )
        session.query(ScheduleChangeRequest).filter(
            (ScheduleChangeRequest.user_id.in_(user_ids))
            | (ScheduleChangeRequest.resolved_by_manager_id.in_(user_ids))
        ).delete(synchronize_session=False)
        session.query(VerificationToken).filter(VerificationToken.user_id.in_(user_ids)).delete(
            synchronize_session=False
        )

    if period_ids:
        session.query(ScheduleEntry).filter(ScheduleEntry.period_id.in_(period_ids)).delete(
            synchronize_session=False
        )
        session.query(ScheduleChangeRequest).filter(
            ScheduleChangeRequest.period_id.in_(period_ids)
        ).delete(synchronize_session=False)
        session.query(CollectionPeriod).filter(CollectionPeriod.id.in_(period_ids)).delete(
            synchronize_session=False
        )

    if user_ids:
        session.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)

    session.commit()


def add_schedule_entries(session, *, user_id: int, period_id: int, start_day: date, days: list[dict]) -> None:
    for offset, payload in enumerate(days):
        session.add(
            ScheduleEntry(
                user_id=user_id,
                period_id=period_id,
                day=start_day + timedelta(days=offset),
                status=payload["status"],
                meta=payload.get("meta"),
            )
        )


def main() -> int:
    session = SessionLocal()
    try:
        log("cleaning previous demo data")
        cleanup_demo_data(session)

        today = datetime.now(timezone.utc).date()
        active_start = next_monday(today)
        active_deadline = datetime.combine(
            today + timedelta(days=3),
            dt_time(hour=18),
            tzinfo=timezone.utc,
        )
        expired_start = active_start - timedelta(days=14)
        expired_deadline = datetime.combine(
            today - timedelta(days=2),
            dt_time(hour=18),
            tzinfo=timezone.utc,
        )

        log("creating demo users")
        manager = User(
            email=MANAGER_EMAIL,
            password_hash=get_password_hash(MANAGER_PASSWORD),
            registered=True,
            is_verified=True,
            full_name="Demo Manager",
            alliance=DEMO_ALLIANCE,
            category="manager",
            role=UserRole.MANAGER,
        )
        employee_1 = User(
            email="employee1@company.ru",
            password_hash=get_password_hash(EMPLOYEE_PASSWORD),
            registered=True,
            is_verified=True,
            full_name="Ivan Petrov",
            alliance=DEMO_ALLIANCE,
            category="operator",
            role=UserRole.USER,
            vacation_days_declared=14,
            vacation_days_approved=14,
            vacation_days_status=VacationDaysStatus.APPROVED,
        )
        employee_2 = User(
            email="employee2@company.ru",
            password_hash=get_password_hash(EMPLOYEE_PASSWORD),
            registered=True,
            is_verified=True,
            full_name="Anna Sidorova",
            alliance=DEMO_ALLIANCE,
            category="operator",
            role=UserRole.USER,
            vacation_days_declared=18,
            vacation_days_approved=16,
            vacation_days_status=VacationDaysStatus.ADJUSTED,
        )
        employee_3 = User(
            email="employee3@company.ru",
            password_hash=get_password_hash(EMPLOYEE_PASSWORD),
            registered=True,
            is_verified=False,
            full_name="Pavel Ivanov",
            alliance=DEMO_ALLIANCE,
            category="operator",
            role=UserRole.USER,
            vacation_days_declared=21,
            vacation_days_status=VacationDaysStatus.PENDING,
        )
        employee_4 = User(
            email="employee4@company.ru",
            password_hash=get_password_hash(EMPLOYEE_PASSWORD),
            registered=True,
            is_verified=True,
            full_name="Maria Smirnova",
            alliance=DEMO_ALLIANCE,
            category="operator",
            role=UserRole.USER,
            vacation_days_declared=10,
            vacation_days_approved=10,
            vacation_days_status=VacationDaysStatus.APPROVED,
        )
        employee_5 = User(
            email="employee5@company.ru",
            password_hash=get_password_hash(EMPLOYEE_PASSWORD),
            registered=True,
            is_verified=True,
            full_name="Oleg Kuznetsov",
            alliance=DEMO_ALLIANCE,
            category="operator",
            role=UserRole.USER,
            vacation_days_declared=7,
            vacation_days_status=VacationDaysStatus.PENDING,
        )

        session.add_all([manager, employee_1, employee_2, employee_3, employee_4, employee_5])
        session.commit()

        log("creating periods")
        active_period = CollectionPeriod(
            alliance=DEMO_ALLIANCE,
            period_start=active_start,
            period_end=active_start + timedelta(days=6),
            deadline=active_deadline,
            is_open=True,
        )
        expired_period = CollectionPeriod(
            alliance=DEMO_ALLIANCE,
            period_start=expired_start,
            period_end=expired_start + timedelta(days=6),
            deadline=expired_deadline,
            is_open=False,
        )
        session.add_all([active_period, expired_period])
        session.commit()
        session.refresh(active_period)
        session.refresh(expired_period)

        log("creating employee templates")
        session.add_all(
            [
                ScheduleTemplate(
                    user_id=employee_1.id,
                    name="5/2 Morning",
                    work_days=5,
                    rest_days=2,
                    shift_start="09:00",
                    shift_end="18:00",
                    has_break=False,
                ),
                ScheduleTemplate(
                    user_id=employee_2.id,
                    name="Split Day",
                    work_days=5,
                    rest_days=2,
                    shift_start="08:00",
                    shift_end="17:00",
                    has_break=False,
                ),
            ]
        )

        log("creating active period schedules")
        add_schedule_entries(
            session,
            user_id=employee_1.id,
            period_id=active_period.id,
            start_day=active_period.period_start,
            days=[
                schedule_shift("09:00", "17:00"),
                schedule_shift("09:00", "17:00"),
                schedule_shift("09:00", "17:00"),
                schedule_shift("09:00", "17:00"),
                schedule_shift("09:00", "17:00"),
                {"status": "dayoff", "meta": None},
                {"status": "dayoff", "meta": None},
            ],
        )
        add_schedule_entries(
            session,
            user_id=employee_2.id,
            period_id=active_period.id,
            start_day=active_period.period_start,
            days=[
                schedule_shift("09:00", "17:00"),
                schedule_shift("09:00", "17:00"),
                schedule_shift("09:00", "17:00"),
                schedule_shift("09:00", "17:00"),
                schedule_shift("09:00", "17:00"),
                schedule_shift("09:00", "17:00"),
                schedule_shift("09:00", "17:00"),
            ],
        )
        add_schedule_entries(
            session,
            user_id=employee_4.id,
            period_id=active_period.id,
            start_day=active_period.period_start,
            days=[
                {"status": "vacation", "meta": None},
                {"status": "vacation", "meta": None},
                schedule_shift("10:00", "18:00"),
                schedule_shift("10:00", "18:00"),
                schedule_shift("10:00", "18:00"),
                {"status": "dayoff", "meta": None},
                {"status": "dayoff", "meta": None},
            ],
        )

        log("creating pending post-deadline change request")
        proposed_schedule = {}
        for offset in range(7):
            current_day = expired_period.period_start + timedelta(days=offset)
            proposed_schedule[current_day.isoformat()] = schedule_shift("11:00", "19:00")

        session.add(
            ScheduleChangeRequest(
                user_id=employee_1.id,
                period_id=expired_period.id,
                status=ScheduleChangeRequestStatus.PENDING,
                employee_comment="Need to fix last week's schedule after outage",
                proposed_schedule=proposed_schedule,
            )
        )

        session.commit()

        log("demo data created")
        print()
        print("Demo accounts:")
        print(f"Manager:  {MANAGER_EMAIL} / {MANAGER_PASSWORD}")
        print(f"Employee: employee1@company.ru / {EMPLOYEE_PASSWORD}")
        print(f"Employee: employee2@company.ru / {EMPLOYEE_PASSWORD}")
        print(f"Employee: employee4@company.ru / {EMPLOYEE_PASSWORD}")
        print()
        print(f"Alliance: {DEMO_ALLIANCE}")
        print(f"Active period start: {active_period.period_start}")
        print(f"Active period deadline: {active_period.deadline.isoformat()}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
