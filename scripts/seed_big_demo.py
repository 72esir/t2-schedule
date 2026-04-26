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

BIG_DEMO_ALLIANCE = "Big Demo Alliance"
BIG_MANAGER_EMAIL = "bigmanager@company.ru"
BIG_EMPLOYEE_PASSWORD = "Employee123!"
BIG_MANAGER_PASSWORD = "Manager123!"
BIG_EMPLOYEE_EMAILS = [f"bigemployee{i:02d}@company.ru" for i in range(1, 31)]


def log(message: str) -> None:
    print(f"[seed-big] {message}")


def next_monday(day: date) -> date:
    days_ahead = (7 - day.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return day + timedelta(days=days_ahead)


def shift(start: str, end: str) -> dict:
    return {"status": "shift", "meta": {"shiftStart": start, "shiftEnd": end}}


def split_shift(start1: str, end1: str, start2: str, end2: str) -> dict:
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


def pattern_5_2(start: str, end: str) -> list[dict]:
    return [
        shift(start, end),
        shift(start, end),
        shift(start, end),
        shift(start, end),
        shift(start, end),
        dayoff(),
        dayoff(),
        shift(start, end),
        shift(start, end),
        shift(start, end),
        shift(start, end),
        shift(start, end),
        dayoff(),
        dayoff(),
    ]


def pattern_split_2_2() -> list[dict]:
    return [
        split_shift("08:00", "12:00", "14:00", "18:00"),
        split_shift("08:00", "12:00", "14:00", "18:00"),
        dayoff(),
        dayoff(),
        split_shift("08:00", "12:00", "14:00", "18:00"),
        split_shift("08:00", "12:00", "14:00", "18:00"),
        dayoff(),
        dayoff(),
        split_shift("08:00", "12:00", "14:00", "18:00"),
        split_shift("08:00", "12:00", "14:00", "18:00"),
        dayoff(),
        dayoff(),
        split_shift("08:00", "12:00", "14:00", "18:00"),
        split_shift("08:00", "12:00", "14:00", "18:00"),
    ]


def pattern_dense_violation() -> list[dict]:
    return [shift("09:00", "17:00") for _ in range(14)]


def pattern_under_hours() -> list[dict]:
    return [
        shift("10:00", "14:00"),
        dayoff(),
        shift("10:00", "14:00"),
        dayoff(),
        shift("10:00", "14:00"),
        dayoff(),
        dayoff(),
        shift("10:00", "14:00"),
        dayoff(),
        shift("10:00", "14:00"),
        dayoff(),
        shift("10:00", "14:00"),
        dayoff(),
        dayoff(),
    ]


def pattern_vacation_mix() -> list[dict]:
    return [
        vacation(),
        vacation(),
        vacation(),
        shift("11:00", "19:00"),
        shift("11:00", "19:00"),
        dayoff(),
        dayoff(),
        shift("11:00", "19:00"),
        shift("11:00", "19:00"),
        shift("11:00", "19:00"),
        dayoff(),
        vacation(),
        vacation(),
        dayoff(),
    ]


def pattern_late_shift() -> list[dict]:
    return pattern_5_2("12:00", "20:00")


def pattern_empty() -> list[dict]:
    return [dayoff() for _ in range(14)]


def cleanup_big_demo_data(session) -> None:
    demo_emails = [BIG_MANAGER_EMAIL, *BIG_EMPLOYEE_EMAILS]

    users = session.query(User).filter(User.email.in_(demo_emails)).all()
    user_ids = [user.id for user in users]
    period_ids = [
        period_id
        for (period_id,) in session.query(CollectionPeriod.id)
        .filter(CollectionPeriod.alliance == BIG_DEMO_ALLIANCE)
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
    timestamp = saved_at or datetime.now(timezone.utc)
    for offset, payload in enumerate(days):
        session.add(
            ScheduleEntry(
                user_id=user_id,
                period_id=period_id,
                day=start_day + timedelta(days=offset),
                status=payload["status"],
                meta=payload.get("meta"),
                created_at=timestamp,
                updated_at=timestamp,
            )
        )


def main() -> int:
    session = SessionLocal()
    try:
        log("cleaning previous big demo data")
        cleanup_big_demo_data(session)

        today = datetime.now(timezone.utc).date()
        active_start = next_monday(today)
        active_deadline = datetime.combine(
            today + timedelta(days=4),
            dt_time(hour=18),
            tzinfo=timezone.utc,
        )

        closed_starts = [active_start - timedelta(days=14 * index) for index in range(1, 6)]
        closed_deadlines = [
            datetime.combine(
                today - timedelta(days=(index * 7) + 1),
                dt_time(hour=18),
                tzinfo=timezone.utc,
            )
            for index in range(1, 6)
        ]
        expired_start = active_start - timedelta(days=14)
        expired_deadline = datetime.combine(
            today - timedelta(days=1),
            dt_time(hour=18),
            tzinfo=timezone.utc,
        )

        log("creating manager and employees")
        manager = User(
            email=BIG_MANAGER_EMAIL,
            password_hash=get_password_hash(BIG_MANAGER_PASSWORD),
            registered=True,
            is_verified=True,
            full_name="Big Demo Manager",
            alliance=BIG_DEMO_ALLIANCE,
            category="manager",
            role=UserRole.MANAGER,
        )
        session.add(manager)

        employees: list[User] = []
        for index, email in enumerate(BIG_EMPLOYEE_EMAILS, start=1):
            verified = index not in {27, 28, 29, 30}
            vacation_status = VacationDaysStatus.APPROVED
            vacation_declared = 14 + (index % 6)
            vacation_approved = vacation_declared

            if index in {9, 10, 11, 12}:
                vacation_status = VacationDaysStatus.PENDING
                vacation_approved = None
            elif index in {13, 14}:
                vacation_status = VacationDaysStatus.ADJUSTED
                vacation_approved = vacation_declared - 2

            employee = User(
                email=email,
                password_hash=get_password_hash(BIG_EMPLOYEE_PASSWORD),
                registered=True,
                is_verified=verified,
                full_name=f"Big Employee {index:02d}",
                alliance=BIG_DEMO_ALLIANCE,
                category="operator",
                role=UserRole.USER,
                vacation_days_declared=vacation_declared,
                vacation_days_approved=vacation_approved,
                vacation_days_status=vacation_status,
            )
            employees.append(employee)
            session.add(employee)

        session.commit()

        log("creating periods")
        active_period = CollectionPeriod(
            alliance=BIG_DEMO_ALLIANCE,
            period_start=active_start,
            period_end=active_start + timedelta(days=13),
            deadline=active_deadline,
            is_open=True,
        )
        closed_periods = [
            CollectionPeriod(
                alliance=BIG_DEMO_ALLIANCE,
                period_start=period_start,
                period_end=period_start + timedelta(days=13),
                deadline=deadline,
                is_open=False,
            )
            for period_start, deadline in zip(closed_starts, closed_deadlines, strict=True)
        ]
        expired_period = CollectionPeriod(
            alliance=BIG_DEMO_ALLIANCE,
            period_start=expired_start,
            period_end=expired_start + timedelta(days=13),
            deadline=expired_deadline,
            is_open=False,
        )
        session.add(active_period)
        session.add_all(closed_periods)
        session.add(expired_period)
        session.commit()
        session.refresh(active_period)
        for period in closed_periods:
            session.refresh(period)
        session.refresh(expired_period)

        log("creating templates")
        template_targets = [
            (employees[0], "Morning 5/2", "09:00", "17:00"),
            (employees[5], "Late 5/2", "12:00", "20:00"),
            (employees[6], "Split Day", "08:00", "18:00"),
            (employees[14], "Dense Shift", "09:00", "17:00"),
        ]
        for user, name, shift_start, shift_end in template_targets:
            session.add(
                ScheduleTemplate(
                    user_id=user.id,
                    name=name,
                    work_days=5,
                    rest_days=2,
                    shift_start=shift_start,
                    shift_end=shift_end,
                    has_break=False,
                )
            )

        log("creating repeated closed periods for streaks and suggestions")
        suggested_employee = employees[5]  # bigemployee06
        suggested_pattern = pattern_late_shift()
        for period in [*closed_periods, expired_period]:
            add_schedule_entries(
                session,
                user_id=suggested_employee.id,
                period_id=period.id,
                start_day=period.period_start,
                days=suggested_pattern,
                saved_at=period.deadline - timedelta(days=1),
            )

        other_patterns = [
            pattern_5_2("09:00", "17:00"),
            pattern_split_2_2(),
            pattern_dense_violation(),
            pattern_under_hours(),
            pattern_vacation_mix(),
            pattern_5_2("10:00", "18:00"),
            pattern_5_2("08:00", "16:00"),
        ]

        for employee_index, employee in enumerate(employees[:20]):
            if employee.id == suggested_employee.id:
                continue
            pattern = other_patterns[employee_index % len(other_patterns)]
            for period_index, period in enumerate(closed_periods[:3]):
                add_schedule_entries(
                    session,
                    user_id=employee.id,
                    period_id=period.id,
                    start_day=period.period_start,
                    days=pattern,
                    saved_at=period.deadline - timedelta(days=1 + (period_index % 2)),
                )

        log("creating active period schedules with variety for excel export")
        active_patterns = [
            pattern_5_2("09:00", "17:00"),
            pattern_split_2_2(),
            pattern_dense_violation(),
            pattern_under_hours(),
            pattern_vacation_mix(),
            pattern_5_2("10:00", "18:00"),
            pattern_5_2("08:00", "16:00"),
            pattern_5_2("07:00", "15:00"),
        ]

        submitted_active_count = 0
        for employee_index, employee in enumerate(employees[:12]):
            pattern = active_patterns[employee_index % len(active_patterns)]
            if employee.id == suggested_employee.id:
                pattern = pattern_empty()
            add_schedule_entries(
                session,
                user_id=employee.id,
                period_id=active_period.id,
                start_day=active_period.period_start,
                days=pattern,
            )
            submitted_active_count += 1

        log("creating pending post-deadline request")
        proposed_schedule = {}
        for offset, payload in enumerate(pattern_5_2("11:00", "19:00")):
            current_day = expired_period.period_start + timedelta(days=offset)
            proposed_schedule[current_day.isoformat()] = payload

        session.add(
            ScheduleChangeRequest(
                user_id=employees[0].id,
                period_id=expired_period.id,
                status=ScheduleChangeRequestStatus.PENDING,
                employee_comment="Need to correct exported schedule after roster changes",
                proposed_schedule=proposed_schedule,
            )
        )

        session.commit()

        verified_count = sum(1 for employee in employees if employee.is_verified)
        log("big demo data created")
        print()
        print("Big demo accounts:")
        print(f"Manager:  {BIG_MANAGER_EMAIL} / {BIG_MANAGER_PASSWORD}")
        print(f"Employee: {suggested_employee.email} / {BIG_EMPLOYEE_PASSWORD}")
        print()
        print(f"Alliance: {BIG_DEMO_ALLIANCE}")
        print(f"Verified employees: {verified_count}")
        print(f"Unverified employees: {len(employees) - verified_count}")
        print(f"Active period start: {active_period.period_start}")
        print(f"Active period end: {active_period.period_end}")
        print(f"Active period deadline: {active_period.deadline.isoformat()}")
        print(f"Submitted employees in active period: {submitted_active_count}")
        print()
        print("Best single employee for combined demo:")
        print(f"- {suggested_employee.email} / {BIG_EMPLOYEE_PASSWORD}")
        print("  Supports:")
        print("  * suggested template for current active period")
        print("  * redeemable streak for bonus exchange")
        print()
        print("Excel/export focus:")
        print(f"- {submitted_active_count} verified employees already have active-period entries")
        print("- multiple schedule patterns and validation violations are present")
        print("- pending verification, vacation moderation, and change request queues are populated")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
