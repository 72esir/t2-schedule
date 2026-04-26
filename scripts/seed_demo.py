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
DEMO_EMPLOYEE_EMAILS = [f"employee{i}@company.ru" for i in range(1, 10)]


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


def schedule_split(start1: str, end1: str, start2: str, end2: str) -> dict:
    return {
        "status": "split",
        "meta": {
            "splitStart1": start1,
            "splitEnd1": end1,
            "splitStart2": start2,
            "splitEnd2": end2,
        },
    }


def dayoff() -> dict:
    return {"status": "dayoff", "meta": None}


def vacation() -> dict:
    return {"status": "vacation", "meta": None}


def cleanup_demo_data(session) -> None:
    demo_emails = [MANAGER_EMAIL, *DEMO_EMPLOYEE_EMAILS]

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


def add_schedule_entries(
    session,
    *,
    user_id: int,
    period_id: int,
    start_day: date,
    days: list[dict],
    saved_at: datetime | None = None,
) -> None:
    for offset, payload in enumerate(days):
        session.add(
            ScheduleEntry(
                user_id=user_id,
                period_id=period_id,
                day=start_day + timedelta(days=offset),
                status=payload["status"],
                meta=payload.get("meta"),
                created_at=saved_at or datetime.now(timezone.utc),
                updated_at=saved_at or datetime.now(timezone.utc),
            )
        )


def repeat_pattern(pattern: list[dict], cycles: int) -> list[dict]:
    result: list[dict] = []
    for _ in range(cycles):
        result.extend(pattern)
    return result


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
        closed_template_start_1 = active_start - timedelta(days=21)
        closed_template_deadline_1 = datetime.combine(
            today - timedelta(days=8),
            dt_time(hour=18),
            tzinfo=timezone.utc,
        )
        closed_template_start_2 = active_start - timedelta(days=14)
        closed_template_deadline_2 = datetime.combine(
            today - timedelta(days=2),
            dt_time(hour=18),
            tzinfo=timezone.utc,
        )
        closed_template_start_3 = active_start - timedelta(days=28)
        closed_template_deadline_3 = datetime.combine(
            today - timedelta(days=15),
            dt_time(hour=18),
            tzinfo=timezone.utc,
        )
        closed_template_start_4 = active_start - timedelta(days=35)
        closed_template_deadline_4 = datetime.combine(
            today - timedelta(days=22),
            dt_time(hour=18),
            tzinfo=timezone.utc,
        )
        closed_template_start_5 = active_start - timedelta(days=42)
        closed_template_deadline_5 = datetime.combine(
            today - timedelta(days=29),
            dt_time(hour=18),
            tzinfo=timezone.utc,
        )
        expired_start = active_start - timedelta(days=7)
        expired_deadline = datetime.combine(
            today - timedelta(days=1),
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
        employee_6 = User(
            email="employee6@company.ru",
            password_hash=get_password_hash(EMPLOYEE_PASSWORD),
            registered=True,
            is_verified=True,
            full_name="Sergey Volkov",
            alliance=DEMO_ALLIANCE,
            category="operator",
            role=UserRole.USER,
            vacation_days_declared=12,
            vacation_days_approved=12,
            vacation_days_status=VacationDaysStatus.APPROVED,
        )
        employee_7 = User(
            email="employee7@company.ru",
            password_hash=get_password_hash(EMPLOYEE_PASSWORD),
            registered=True,
            is_verified=True,
            full_name="Elena Kozlova",
            alliance=DEMO_ALLIANCE,
            category="operator",
            role=UserRole.USER,
            vacation_days_declared=5,
            vacation_days_approved=5,
            vacation_days_status=VacationDaysStatus.APPROVED,
        )
        employee_8 = User(
            email="employee8@company.ru",
            password_hash=get_password_hash(EMPLOYEE_PASSWORD),
            registered=True,
            is_verified=True,
            full_name="Dmitry Orlov",
            alliance=DEMO_ALLIANCE,
            category="operator",
            role=UserRole.USER,
            vacation_days_declared=9,
            vacation_days_status=VacationDaysStatus.PENDING,
        )
        employee_9 = User(
            email="employee9@company.ru",
            password_hash=get_password_hash(EMPLOYEE_PASSWORD),
            registered=True,
            is_verified=True,
            full_name="Natalia Fedorova",
            alliance=DEMO_ALLIANCE,
            category="operator",
            role=UserRole.USER,
            vacation_days_declared=4,
            vacation_days_approved=4,
            vacation_days_status=VacationDaysStatus.APPROVED,
        )

        session.add_all(
            [
                manager,
                employee_1,
                employee_2,
                employee_3,
                employee_4,
                employee_5,
                employee_6,
                employee_7,
                employee_8,
                employee_9,
            ]
        )
        session.commit()

        log("creating periods")
        active_period = CollectionPeriod(
            alliance=DEMO_ALLIANCE,
            period_start=active_start,
            period_end=active_start + timedelta(days=6),
            deadline=active_deadline,
            is_open=True,
        )
        closed_template_period_1 = CollectionPeriod(
            alliance=DEMO_ALLIANCE,
            period_start=closed_template_start_1,
            period_end=closed_template_start_1 + timedelta(days=6),
            deadline=closed_template_deadline_1,
            is_open=False,
        )
        closed_template_period_2 = CollectionPeriod(
            alliance=DEMO_ALLIANCE,
            period_start=closed_template_start_2,
            period_end=closed_template_start_2 + timedelta(days=6),
            deadline=closed_template_deadline_2,
            is_open=False,
        )
        closed_template_period_3 = CollectionPeriod(
            alliance=DEMO_ALLIANCE,
            period_start=closed_template_start_3,
            period_end=closed_template_start_3 + timedelta(days=6),
            deadline=closed_template_deadline_3,
            is_open=False,
        )
        closed_template_period_4 = CollectionPeriod(
            alliance=DEMO_ALLIANCE,
            period_start=closed_template_start_4,
            period_end=closed_template_start_4 + timedelta(days=6),
            deadline=closed_template_deadline_4,
            is_open=False,
        )
        closed_template_period_5 = CollectionPeriod(
            alliance=DEMO_ALLIANCE,
            period_start=closed_template_start_5,
            period_end=closed_template_start_5 + timedelta(days=6),
            deadline=closed_template_deadline_5,
            is_open=False,
        )
        expired_period = CollectionPeriod(
            alliance=DEMO_ALLIANCE,
            period_start=expired_start,
            period_end=expired_start + timedelta(days=6),
            deadline=expired_deadline,
            is_open=False,
        )
        session.add_all(
            [
                active_period,
                closed_template_period_5,
                closed_template_period_4,
                closed_template_period_1,
                closed_template_period_2,
                closed_template_period_3,
                expired_period,
            ]
        )
        session.commit()
        session.refresh(active_period)
        session.refresh(closed_template_period_1)
        session.refresh(closed_template_period_2)
        session.refresh(closed_template_period_3)
        session.refresh(closed_template_period_4)
        session.refresh(closed_template_period_5)
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
                ScheduleTemplate(
                    user_id=employee_6.id,
                    name="Late Start 5/2",
                    work_days=5,
                    rest_days=2,
                    shift_start="12:00",
                    shift_end="20:00",
                    has_break=False,
                ),
                ScheduleTemplate(
                    user_id=employee_7.id,
                    name="Split 2/2",
                    work_days=2,
                    rest_days=2,
                    shift_start="08:00",
                    shift_end="20:00",
                    has_break=False,
                ),
            ]
        )

        log("creating repeated closed period schedules for suggestion")
        repeated_days_employee_1 = [
            schedule_shift("09:00", "17:00"),
            schedule_shift("09:00", "17:00"),
            schedule_shift("09:00", "17:00"),
            schedule_shift("09:00", "17:00"),
            schedule_shift("09:00", "17:00"),
            dayoff(),
            dayoff(),
        ]
        repeated_days_employee_2 = [
            schedule_split("08:00", "12:00", "14:00", "18:00"),
            schedule_split("08:00", "12:00", "14:00", "18:00"),
            schedule_split("08:00", "12:00", "14:00", "18:00"),
            schedule_split("08:00", "12:00", "14:00", "18:00"),
            schedule_split("08:00", "12:00", "14:00", "18:00"),
            dayoff(),
            dayoff(),
        ]
        repeated_days_employee_6 = [
            schedule_shift("12:00", "20:00"),
            schedule_shift("12:00", "20:00"),
            schedule_shift("12:00", "20:00"),
            schedule_shift("12:00", "20:00"),
            schedule_shift("12:00", "20:00"),
            dayoff(),
            dayoff(),
        ]
        repeated_days_employee_7 = [
            schedule_split("09:00", "13:00", "15:00", "19:00"),
            schedule_split("09:00", "13:00", "15:00", "19:00"),
            dayoff(),
            dayoff(),
            schedule_split("09:00", "13:00", "15:00", "19:00"),
            schedule_split("09:00", "13:00", "15:00", "19:00"),
            dayoff(),
        ]

        add_schedule_entries(
            session,
            user_id=employee_1.id,
            period_id=closed_template_period_1.id,
            start_day=closed_template_period_1.period_start,
            days=repeated_days_employee_1,
            saved_at=closed_template_period_1.deadline - timedelta(days=1),
        )
        add_schedule_entries(
            session,
            user_id=employee_1.id,
            period_id=closed_template_period_2.id,
            start_day=closed_template_period_2.period_start,
            days=repeated_days_employee_1,
            saved_at=closed_template_period_2.deadline - timedelta(days=1),
        )
        add_schedule_entries(
            session,
            user_id=employee_2.id,
            period_id=closed_template_period_1.id,
            start_day=closed_template_period_1.period_start,
            days=repeated_days_employee_2,
            saved_at=closed_template_period_1.deadline - timedelta(days=1),
        )
        add_schedule_entries(
            session,
            user_id=employee_2.id,
            period_id=closed_template_period_2.id,
            start_day=closed_template_period_2.period_start,
            days=repeated_days_employee_2,
            saved_at=closed_template_period_2.deadline - timedelta(days=1),
        )
        add_schedule_entries(
            session,
            user_id=employee_6.id,
            period_id=closed_template_period_5.id,
            start_day=closed_template_period_5.period_start,
            days=repeated_days_employee_6,
            saved_at=closed_template_period_5.deadline - timedelta(days=1),
        )
        add_schedule_entries(
            session,
            user_id=employee_6.id,
            period_id=closed_template_period_4.id,
            start_day=closed_template_period_4.period_start,
            days=repeated_days_employee_6,
            saved_at=closed_template_period_4.deadline - timedelta(days=1),
        )
        add_schedule_entries(
            session,
            user_id=employee_6.id,
            period_id=closed_template_period_2.id,
            start_day=closed_template_period_2.period_start,
            days=repeated_days_employee_6,
            saved_at=closed_template_period_2.deadline - timedelta(days=1),
        )
        add_schedule_entries(
            session,
            user_id=employee_6.id,
            period_id=closed_template_period_3.id,
            start_day=closed_template_period_3.period_start,
            days=repeated_days_employee_6,
            saved_at=closed_template_period_3.deadline - timedelta(days=1),
        )
        add_schedule_entries(
            session,
            user_id=employee_6.id,
            period_id=closed_template_period_1.id,
            start_day=closed_template_period_1.period_start,
            days=repeated_days_employee_6,
            saved_at=closed_template_period_1.deadline - timedelta(days=1),
        )
        add_schedule_entries(
            session,
            user_id=employee_6.id,
            period_id=expired_period.id,
            start_day=expired_period.period_start,
            days=repeated_days_employee_6,
            saved_at=expired_period.deadline - timedelta(days=1),
        )
        add_schedule_entries(
            session,
            user_id=employee_7.id,
            period_id=closed_template_period_1.id,
            start_day=closed_template_period_1.period_start,
            days=repeated_days_employee_7,
            saved_at=closed_template_period_1.deadline - timedelta(days=1),
        )
        add_schedule_entries(
            session,
            user_id=employee_7.id,
            period_id=closed_template_period_3.id,
            start_day=closed_template_period_3.period_start,
            days=repeated_days_employee_7,
            saved_at=closed_template_period_3.deadline - timedelta(days=1),
        )

        log("creating active period schedules")
        add_schedule_entries(
            session,
            user_id=employee_1.id,
            period_id=active_period.id,
            start_day=active_period.period_start,
            days=[
                dayoff(),
                dayoff(),
                dayoff(),
                dayoff(),
                dayoff(),
                dayoff(),
                dayoff(),
            ],
        )
        add_schedule_entries(
            session,
            user_id=employee_2.id,
            period_id=active_period.id,
            start_day=active_period.period_start,
            days=[
                dayoff(),
                dayoff(),
                dayoff(),
                dayoff(),
                dayoff(),
                dayoff(),
                dayoff(),
            ],
        )
        add_schedule_entries(
            session,
            user_id=employee_4.id,
            period_id=active_period.id,
            start_day=active_period.period_start,
            days=[
                vacation(),
                vacation(),
                schedule_shift("10:00", "18:00"),
                schedule_shift("10:00", "18:00"),
                schedule_shift("10:00", "18:00"),
                dayoff(),
                dayoff(),
            ],
        )
        add_schedule_entries(
            session,
            user_id=employee_5.id,
            period_id=active_period.id,
            start_day=active_period.period_start,
            days=[
                schedule_shift("08:00", "16:00"),
                schedule_shift("08:00", "16:00"),
                schedule_shift("08:00", "16:00"),
                schedule_shift("08:00", "16:00"),
                dayoff(),
                dayoff(),
                dayoff(),
            ],
        )
        add_schedule_entries(
            session,
            user_id=employee_6.id,
            period_id=active_period.id,
            start_day=active_period.period_start,
            days=[
                dayoff(),
                dayoff(),
                dayoff(),
                dayoff(),
                dayoff(),
                dayoff(),
                dayoff(),
            ],
        )
        add_schedule_entries(
            session,
            user_id=employee_7.id,
            period_id=active_period.id,
            start_day=active_period.period_start,
            days=[
                dayoff(),
                dayoff(),
                dayoff(),
                dayoff(),
                dayoff(),
                dayoff(),
                dayoff(),
            ],
        )
        add_schedule_entries(
            session,
            user_id=employee_8.id,
            period_id=active_period.id,
            start_day=active_period.period_start,
            days=[
                schedule_shift("11:00", "19:00"),
                schedule_shift("11:00", "19:00"),
                dayoff(),
                schedule_shift("11:00", "19:00"),
                schedule_shift("11:00", "19:00"),
                dayoff(),
                dayoff(),
            ],
        )
        add_schedule_entries(
            session,
            user_id=employee_9.id,
            period_id=active_period.id,
            start_day=active_period.period_start,
            days=[
                schedule_split("10:00", "14:00", "16:00", "20:00"),
                schedule_split("10:00", "14:00", "16:00", "20:00"),
                schedule_split("10:00", "14:00", "16:00", "20:00"),
                dayoff(),
                dayoff(),
                schedule_shift("12:00", "20:00"),
                dayoff(),
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
        print(f"Employee: employee6@company.ru / {EMPLOYEE_PASSWORD}")
        print(f"Employee: employee7@company.ru / {EMPLOYEE_PASSWORD}")
        print()
        print(f"Alliance: {DEMO_ALLIANCE}")
        print(f"Active period start: {active_period.period_start}")
        print(f"Active period deadline: {active_period.deadline.isoformat()}")
        print()
        print("Single-account demo for both features:")
        print(f"- employee6@company.ru / {EMPLOYEE_PASSWORD}")
        print("  Supports:")
        print("  * suggested template for current active period")
        print("  * redeemable streak for bonus exchange")
        print("Suggested template should be available for:")
        print("- employee1@company.ru")
        print("- employee2@company.ru")
        print("- employee6@company.ru")
        print("- employee7@company.ru")
        print()
        print("Redeemable streak should be available for:")
        print("- employee6@company.ru")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
