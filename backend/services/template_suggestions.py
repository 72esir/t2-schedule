from __future__ import annotations

import json
from collections import defaultdict
from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from backend.models import CollectionPeriod, ScheduleEntry, User


def _period_length(period: CollectionPeriod) -> int:
    return (period.period_end - period.period_start).days + 1


def _normalize_payload(entry: ScheduleEntry) -> dict[str, Any]:
    return {
        "status": entry.status,
        "meta": entry.meta,
    }


def _payload_signature(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True)


def _build_period_signature(
    session: Session,
    *,
    user_id: int,
    period: CollectionPeriod,
) -> tuple[tuple[str, ...], list[dict[str, Any]]] | None:
    entries = (
        session.query(ScheduleEntry)
        .filter(
            ScheduleEntry.user_id == user_id,
            ScheduleEntry.period_id == period.id,
        )
        .all()
    )

    expected_days = _period_length(period)
    if len(entries) != expected_days:
        return None

    entries_by_day = {entry.day: entry for entry in entries}
    payloads: list[dict[str, Any]] = []
    signature_parts: list[str] = []

    for offset in range(expected_days):
        current_day = period.period_start + timedelta(days=offset)
        entry = entries_by_day.get(current_day)
        if entry is None:
            return None

        payload = _normalize_payload(entry)
        payloads.append(payload)
        signature_parts.append(_payload_signature(payload))

    return tuple(signature_parts), payloads


def build_suggested_template_for_current_period(
    session: Session,
    *,
    user: User,
    current_period: CollectionPeriod | None,
) -> dict[str, Any]:
    if not current_period:
        return {
            "has_suggestion": False,
            "period_id": None,
            "match_count": 0,
            "source_period_ids": [],
            "days": {},
        }

    candidate_periods = (
        session.query(CollectionPeriod)
        .filter(
            CollectionPeriod.alliance == user.alliance,
            CollectionPeriod.id != current_period.id,
            CollectionPeriod.is_open.is_(False),
        )
        .order_by(CollectionPeriod.period_start.desc())
        .all()
    )

    target_length = _period_length(current_period)
    signatures: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    source_period_ids: defaultdict[tuple[str, ...], list[int]] = defaultdict(list)

    for period in candidate_periods:
        if _period_length(period) != target_length:
            continue

        signature_payload = _build_period_signature(session, user_id=user.id, period=period)
        if signature_payload is None:
            continue

        signature, payloads = signature_payload
        signatures[signature] = payloads
        source_period_ids[signature].append(period.id)

    if not source_period_ids:
        return {
            "has_suggestion": False,
            "period_id": current_period.id,
            "match_count": 0,
            "source_period_ids": [],
            "days": {},
        }

    best_signature, matched_period_ids = max(
        source_period_ids.items(),
        key=lambda item: (len(item[1]), max(item[1])),
    )

    if len(matched_period_ids) < 2:
        return {
            "has_suggestion": False,
            "period_id": current_period.id,
            "match_count": len(matched_period_ids),
            "source_period_ids": matched_period_ids,
            "days": {},
        }

    payloads = signatures[best_signature]
    suggested_days = {
        current_period.period_start + timedelta(days=offset): payload
        for offset, payload in enumerate(payloads)
    }

    return {
        "has_suggestion": True,
        "period_id": current_period.id,
        "match_count": len(matched_period_ids),
        "source_period_ids": matched_period_ids,
        "days": suggested_days,
    }
