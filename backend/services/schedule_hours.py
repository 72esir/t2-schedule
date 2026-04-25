from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, Iterable

from backend.models import ScheduleEntry


def _time_to_minutes(value: str) -> int | None:
    try:
        hours_str, minutes_str = value.split(":")
        hours = int(hours_str)
        minutes = int(minutes_str)
    except (AttributeError, ValueError):
        return None

    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        return None
    return hours * 60 + minutes


def _entry_hours(entry: ScheduleEntry) -> float:
    meta = entry.meta or {}

    if entry.status == "shift":
        start = _time_to_minutes(meta.get("shiftStart"))
        end = _time_to_minutes(meta.get("shiftEnd"))
        if start is None or end is None or start >= end:
            return 0.0
        return round((end - start) / 60, 2)

    if entry.status == "split":
        start1 = _time_to_minutes(meta.get("splitStart1"))
        end1 = _time_to_minutes(meta.get("splitEnd1"))
        start2 = _time_to_minutes(meta.get("splitStart2"))
        end2 = _time_to_minutes(meta.get("splitEnd2"))
        if None in (start1, end1, start2, end2):
            return 0.0
        if start1 >= end1 or start2 >= end2 or end1 > start2:
            return 0.0
        return round(((end1 - start1) + (end2 - start2)) / 60, 2)

    return 0.0


def _is_work_day(entry: ScheduleEntry) -> bool:
    return entry.status in {"shift", "split"} and _entry_hours(entry) > 0


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def build_schedule_summary(entries: Iterable[ScheduleEntry]) -> Dict:
    sorted_entries = sorted(entries, key=lambda entry: entry.day)

    daily_hours: Dict[date, float] = {}
    weekly_hours: Dict[date, float] = defaultdict(float)
    period_total_hours = 0.0
    vacation_days_count = 0
    current_streak = 0
    max_work_streak = 0

    for entry in sorted_entries:
        hours = _entry_hours(entry)
        daily_hours[entry.day] = hours
        weekly_hours[_week_start(entry.day)] += hours
        period_total_hours += hours

        if entry.status == "vacation":
            vacation_days_count += 1

        if _is_work_day(entry):
            current_streak += 1
            max_work_streak = max(max_work_streak, current_streak)
        else:
            current_streak = 0

    return {
        "daily_hours": {day: round(hours, 2) for day, hours in daily_hours.items()},
        "weekly_hours": {day: round(hours, 2) for day, hours in weekly_hours.items()},
        "period_total_hours": round(period_total_hours, 2),
        "vacation_days_count": vacation_days_count,
        "max_work_streak": max_work_streak,
    }
