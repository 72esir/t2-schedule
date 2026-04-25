from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.models import CollectionPeriod, ScheduleChangeRequest, ScheduleEntry, User, UserRole


@dataclass
class PeriodStreakResult:
    period_id: int
    period_start: datetime | None
    period_end: datetime | None
    deadline: datetime
    success: bool
    reason: str


def _entry_saved_before_deadline(entry: ScheduleEntry, deadline: datetime) -> bool:
    saved_at = entry.updated_at or entry.created_at
    return saved_at <= deadline


def _period_result_for_user(
    db: Session,
    *,
    user_id: int,
    period: CollectionPeriod,
) -> PeriodStreakResult:
    entries = (
        db.query(ScheduleEntry)
        .filter(
            ScheduleEntry.user_id == user_id,
            ScheduleEntry.period_id == period.id,
        )
        .all()
    )
    if not entries:
        return PeriodStreakResult(
            period_id=period.id,
            period_start=period.period_start,
            period_end=period.period_end,
            deadline=period.deadline,
            success=False,
            reason="no_schedule",
        )

    if not all(_entry_saved_before_deadline(entry, period.deadline) for entry in entries):
        return PeriodStreakResult(
            period_id=period.id,
            period_start=period.period_start,
            period_end=period.period_end,
            deadline=period.deadline,
            success=False,
            reason="saved_after_deadline",
        )

    has_change_request = (
        db.query(ScheduleChangeRequest.id)
        .filter(
            ScheduleChangeRequest.user_id == user_id,
            ScheduleChangeRequest.period_id == period.id,
        )
        .first()
        is not None
    )
    if has_change_request:
        return PeriodStreakResult(
            period_id=period.id,
            period_start=period.period_start,
            period_end=period.period_end,
            deadline=period.deadline,
            success=False,
            reason="late_change_request",
        )

    return PeriodStreakResult(
        period_id=period.id,
        period_start=period.period_start,
        period_end=period.period_end,
        deadline=period.deadline,
        success=True,
        reason="on_time",
    )


def build_user_streak(db: Session, *, user: User) -> dict:
    now = datetime.now(timezone.utc)
    periods = (
        db.query(CollectionPeriod)
        .filter(
            CollectionPeriod.alliance == user.alliance,
            CollectionPeriod.deadline <= now,
        )
        .order_by(CollectionPeriod.period_start.desc())
        .all()
    )

    history = [
        _period_result_for_user(db, user_id=user.id, period=period)
        for period in periods
    ]

    current_streak = 0
    for result in history:
        if result.success:
            current_streak += 1
        else:
            break

    longest_streak = 0
    running = 0
    for result in reversed(history):
        if result.success:
            running += 1
            longest_streak = max(longest_streak, running)
        else:
            running = 0

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "completed_periods_count": sum(1 for result in history if result.success),
        "evaluated_periods_count": len(history),
        "history": [
            {
                "period_id": result.period_id,
                "period_start": result.period_start,
                "period_end": result.period_end,
                "deadline": result.deadline,
                "success": result.success,
                "reason": result.reason,
            }
            for result in history[:10]
        ],
    }


def build_alliance_streak_leaderboard(db: Session, *, alliance: str) -> list[dict]:
    users = (
        db.query(User)
        .filter(
            User.alliance == alliance,
            User.role == UserRole.USER,
            User.is_verified.is_(True),
        )
        .all()
    )

    leaderboard = []
    for user in users:
        streak = build_user_streak(db, user=user)
        leaderboard.append(
            {
                "user_id": user.id,
                "full_name": user.full_name or user.email or f"User {user.id}",
                "email": user.email,
                "current_streak": streak["current_streak"],
                "longest_streak": streak["longest_streak"],
                "completed_periods_count": streak["completed_periods_count"],
            }
        )

    leaderboard.sort(
        key=lambda item: (
            -item["current_streak"],
            -item["longest_streak"],
            -item["completed_periods_count"],
            (item["full_name"] or "").lower(),
        )
    )
    return leaderboard
