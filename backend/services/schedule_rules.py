from datetime import date
from typing import Dict, Iterable, List

from backend.models import ScheduleEntry
from backend.services.schedule_hours import build_schedule_summary


def build_schedule_validation(entries: Iterable[ScheduleEntry]) -> Dict:
    entry_list = list(entries)
    summary = build_schedule_summary(entry_list)
    violations: List[Dict] = []

    for week_start, hours in summary["weekly_hours"].items():
        if hours < 40:
            violations.append(
                {
                    "code": "WEEKLY_HOURS_UNDER",
                    "level": "warning",
                    "message": f"Недобор часов за неделю, начиная с {week_start}",
                    "context": {
                        "week_start": week_start,
                        "actual_hours": hours,
                        "required_hours": 40,
                        "difference": round(40 - hours, 2),
                    },
                }
            )
        elif hours > 40:
            violations.append(
                {
                    "code": "WEEKLY_HOURS_OVER",
                    "level": "warning",
                    "message": f"Переработка за неделю, начиная с {week_start}",
                    "context": {
                        "week_start": week_start,
                        "actual_hours": hours,
                        "required_hours": 40,
                        "difference": round(hours - 40, 2),
                    },
                }
            )

    if summary["max_work_streak"] > 6:
        violations.append(
            {
                "code": "WORK_STREAK_OVER_6",
                "level": "warning",
                "message": "Больше 6 рабочих дней подряд",
                "context": {
                    "max_work_streak": summary["max_work_streak"],
                    "allowed_max": 6,
                },
            }
        )

    return {
        "is_valid": len(violations) == 0,
        "violations": violations,
        "summary": summary,
    }
