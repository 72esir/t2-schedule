import json
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.core import get_current_verified_user
from backend.core.config import settings
from backend.db import get_db
from backend.models import CollectionPeriod, GoogleCalendarConnection, User
from backend.schemas import (
    GoogleCalendarAvailabilityDayOut,
    GoogleCalendarAvailabilityOut,
    GoogleCalendarBusyIntervalOut,
    GoogleCalendarConnectionStatusOut,
    GoogleCalendarListItemOut,
    GoogleOAuthCallbackOut,
    GoogleOAuthConnectOut,
    GoogleCalendarSuggestedScheduleOut,
)
from backend.models import ScheduleEntry

router = APIRouter(prefix="/integrations/google", tags=["integrations"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_CALENDAR_LIST_URL = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
GOOGLE_CALENDAR_EVENTS_URL_TEMPLATE = "https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
GOOGLE_STATE_TTL_MINUTES = 10
WORKDAY_START_HOUR = 8
WORKDAY_END_HOUR = 22
TARGET_SHIFT_HOURS = 8
MIN_SHIFT_HOURS = 4


def _get_google_scopes() -> list[str]:
    return [scope for scope in settings.GOOGLE_CALENDAR_SCOPES.split() if scope.strip()]


def _build_state_token(*, user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "purpose": "google_oauth_state",
        "exp": int((now + timedelta(minutes=GOOGLE_STATE_TTL_MINUTES)).timestamp()),
        "iat": int(now.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _decode_state_token(token: str) -> int:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid Google OAuth state") from exc

    if payload.get("purpose") != "google_oauth_state":
        raise HTTPException(status_code=400, detail="Invalid Google OAuth state")

    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid Google OAuth state") from exc


def _require_google_oauth_configured() -> None:
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Google Calendar integration is not configured")


def _json_post(url: str, payload: dict, headers: Optional[dict[str, str]] = None) -> dict:
    body = urlencode(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            **(headers or {}),
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"Google token exchange failed: {detail}") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail="Google token exchange failed") from exc


def _json_get(url: str, headers: Optional[dict[str, str]] = None) -> dict:
    request = Request(url, headers=headers or {}, method="GET")
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"Google request failed: {detail}") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail="Google request failed") from exc


def _get_current_period(db: Session, alliance: Optional[str]) -> Optional[CollectionPeriod]:
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


def _get_period_for_user(
    *,
    db: Session,
    current_user: User,
    period_id: Optional[int],
) -> CollectionPeriod:
    if period_id is None:
        period = _get_current_period(db, current_user.alliance)
        if not period:
            raise HTTPException(status_code=404, detail="No active period found")
        return period

    period = db.query(CollectionPeriod).filter(CollectionPeriod.id == period_id).first()
    if not period:
        raise HTTPException(status_code=404, detail="Period not found")
    if period.alliance != current_user.alliance:
        raise HTTPException(status_code=403, detail="No access to period from another alliance")
    return period


def _get_connection_or_404(*, db: Session, user_id: int) -> GoogleCalendarConnection:
    connection = (
        db.query(GoogleCalendarConnection)
        .filter(GoogleCalendarConnection.user_id == user_id)
        .first()
    )
    if not connection:
        raise HTTPException(status_code=404, detail="Google Calendar is not connected")
    return connection


def _refresh_access_token_if_needed(*, db: Session, connection: GoogleCalendarConnection) -> GoogleCalendarConnection:
    if not connection.token_expires_at:
        return connection

    now = datetime.now(timezone.utc)
    expires_at = connection.token_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at > now + timedelta(seconds=60):
        return connection
    if not connection.refresh_token:
        return connection

    token_data = _json_post(
        GOOGLE_TOKEN_URL,
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": connection.refresh_token,
            "grant_type": "refresh_token",
        },
    )

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=502, detail="Google token refresh failed")

    connection.access_token = access_token
    connection.token_type = token_data.get("token_type") or connection.token_type
    connection.scope = token_data.get("scope") or connection.scope

    expires_in = token_data.get("expires_in")
    if expires_in is not None:
        try:
            connection.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        except (TypeError, ValueError):
            pass

    db.commit()
    db.refresh(connection)
    return connection


def _authorized_google_get(*, db: Session, connection: GoogleCalendarConnection, url: str) -> dict:
    connection = _refresh_access_token_if_needed(db=db, connection=connection)
    return _json_get(
        url,
        headers={"Authorization": f"Bearer {connection.access_token}"},
    )


def _parse_google_event_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _extract_busy_interval(event: dict) -> tuple[Optional[date], Optional[GoogleCalendarBusyIntervalOut], bool]:
    start_payload = event.get("start", {})
    end_payload = event.get("end", {})

    if "date" in start_payload:
        day = date.fromisoformat(start_payload["date"])
        return day, None, True

    start_raw = start_payload.get("dateTime")
    end_raw = end_payload.get("dateTime")
    if not start_raw or not end_raw:
        return None, None, False

    start_dt = _parse_google_event_datetime(start_raw)
    end_dt = _parse_google_event_datetime(end_raw)
    return start_dt.date(), GoogleCalendarBusyIntervalOut(start=start_dt, end=end_dt), False


def _utc_day_window(day: date) -> tuple[datetime, datetime]:
    start_dt = datetime.combine(day, time(hour=WORKDAY_START_HOUR), tzinfo=timezone.utc)
    end_dt = datetime.combine(day, time(hour=WORKDAY_END_HOUR), tzinfo=timezone.utc)
    return start_dt, end_dt


def _clip_interval_to_day(
    interval: GoogleCalendarBusyIntervalOut,
    *,
    day: date,
) -> Optional[tuple[datetime, datetime]]:
    day_start, day_end = _utc_day_window(day)
    start = max(interval.start, day_start)
    end = min(interval.end, day_end)
    if end <= start:
        return None
    return start, end


def _merge_intervals(intervals: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    if not intervals:
        return []
    intervals.sort(key=lambda item: item[0])
    merged: list[tuple[datetime, datetime]] = [intervals[0]]
    for start, end in intervals[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def _build_free_windows(
    *,
    day: date,
    busy_intervals: list[GoogleCalendarBusyIntervalOut],
) -> list[tuple[datetime, datetime]]:
    clipped = []
    for interval in busy_intervals:
        clipped_interval = _clip_interval_to_day(interval, day=day)
        if clipped_interval:
            clipped.append(clipped_interval)
    merged_busy = _merge_intervals(clipped)

    day_start, day_end = _utc_day_window(day)
    if not merged_busy:
        return [(day_start, day_end)]

    free_windows: list[tuple[datetime, datetime]] = []
    cursor = day_start
    for busy_start, busy_end in merged_busy:
        if busy_start > cursor:
            free_windows.append((cursor, busy_start))
        cursor = max(cursor, busy_end)
    if cursor < day_end:
        free_windows.append((cursor, day_end))
    return free_windows


def _minutes_between(start: datetime, end: datetime) -> int:
    return max(int((end - start).total_seconds() // 60), 0)


def _minutes_to_hhmm(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%H:%M")


def _slice_window(start: datetime, end: datetime, minutes: int) -> tuple[datetime, datetime]:
    available = _minutes_between(start, end)
    actual = min(available, minutes)
    return start, start + timedelta(minutes=actual)


def _suggest_day_from_availability(
    *,
    day: date,
    availability: GoogleCalendarAvailabilityDayOut,
) -> dict:
    if availability.all_day:
        return {"status": "dayoff", "meta": None}

    free_windows = _build_free_windows(day=day, busy_intervals=availability.busy_intervals)
    long_windows = [
        window
        for window in free_windows
        if _minutes_between(window[0], window[1]) >= MIN_SHIFT_HOURS * 60
    ]
    if not long_windows:
        return {"status": "dayoff", "meta": None}

    single_shift_window = next(
        (window for window in long_windows if _minutes_between(window[0], window[1]) >= TARGET_SHIFT_HOURS * 60),
        None,
    )
    if single_shift_window:
        shift_start, shift_end = _slice_window(single_shift_window[0], single_shift_window[1], TARGET_SHIFT_HOURS * 60)
        return {
            "status": "shift",
            "meta": {
                "shiftStart": _minutes_to_hhmm(shift_start),
                "shiftEnd": _minutes_to_hhmm(shift_end),
            },
        }

    if len(long_windows) >= 2:
        first_start, first_end = _slice_window(long_windows[0][0], long_windows[0][1], MIN_SHIFT_HOURS * 60)
        second_start, second_end = _slice_window(long_windows[1][0], long_windows[1][1], MIN_SHIFT_HOURS * 60)
        if _minutes_between(first_start, first_end) >= MIN_SHIFT_HOURS * 60 and _minutes_between(second_start, second_end) >= MIN_SHIFT_HOURS * 60:
            return {
                "status": "split",
                "meta": {
                    "splitStart1": _minutes_to_hhmm(first_start),
                    "splitEnd1": _minutes_to_hhmm(first_end),
                    "splitStart2": _minutes_to_hhmm(second_start),
                    "splitEnd2": _minutes_to_hhmm(second_end),
                },
            }

    best_window = max(long_windows, key=lambda item: _minutes_between(item[0], item[1]))
    shift_minutes = min(_minutes_between(best_window[0], best_window[1]), TARGET_SHIFT_HOURS * 60)
    shift_start, shift_end = _slice_window(best_window[0], best_window[1], shift_minutes)
    return {
        "status": "shift",
        "meta": {
            "shiftStart": _minutes_to_hhmm(shift_start),
            "shiftEnd": _minutes_to_hhmm(shift_end),
        },
    }


def _build_availability_for_period(
    *,
    db: Session,
    connection: GoogleCalendarConnection,
    period: CollectionPeriod,
    calendar_id: str,
) -> GoogleCalendarAvailabilityOut:
    time_min = datetime.combine(period.period_start, time.min, tzinfo=timezone.utc)
    time_max = datetime.combine(period.period_end + timedelta(days=1), time.min, tzinfo=timezone.utc)
    query = urlencode(
        {
            "singleEvents": "true",
            "orderBy": "startTime",
            "timeMin": time_min.isoformat().replace("+00:00", "Z"),
            "timeMax": time_max.isoformat().replace("+00:00", "Z"),
            "maxResults": 2500,
        }
    )
    url = GOOGLE_CALENDAR_EVENTS_URL_TEMPLATE.format(calendar_id=quote(calendar_id, safe="")) + f"?{query}"
    payload = _authorized_google_get(
        db=db,
        connection=connection,
        url=url,
    )

    days: dict[date, GoogleCalendarAvailabilityDayOut] = {}
    for offset in range((period.period_end - period.period_start).days + 1):
        day = period.period_start + timedelta(days=offset)
        days[day] = GoogleCalendarAvailabilityDayOut()

    for event in payload.get("items", []):
        day, interval, is_all_day = _extract_busy_interval(event)
        if day is None or day not in days:
            continue

        day_state = days[day]
        day_state.event_count += 1
        if is_all_day:
            day_state.all_day = True
            continue
        if interval:
            day_state.busy_intervals.append(interval)

    for day_state in days.values():
        day_state.busy_intervals.sort(key=lambda item: item.start)

    return GoogleCalendarAvailabilityOut(
        period_id=period.id,
        calendar_id=calendar_id,
        period_start=period.period_start,
        period_end=period.period_end,
        time_zone=payload.get("timeZone"),
        days=days,
    )


def _build_suggested_schedule_from_availability(
    *,
    availability: GoogleCalendarAvailabilityOut,
) -> GoogleCalendarSuggestedScheduleOut:
    suggested_days = {
        day: _suggest_day_from_availability(day=day, availability=day_availability)
        for day, day_availability in availability.days.items()
    }
    suggested_days_count = sum(1 for payload in suggested_days.values() if payload["status"] != "dayoff")
    return GoogleCalendarSuggestedScheduleOut(
        period_id=availability.period_id,
        calendar_id=availability.calendar_id,
        period_start=availability.period_start,
        period_end=availability.period_end,
        suggested_days_count=suggested_days_count,
        days=suggested_days,
    )


def _redirect_or_json(*, success: bool, email: Optional[str] = None, error: Optional[str] = None):
    if success and settings.GOOGLE_OAUTH_SUCCESS_REDIRECT_URL:
        url = f"{settings.GOOGLE_OAUTH_SUCCESS_REDIRECT_URL}?google_calendar=connected"
        return RedirectResponse(url=url, status_code=302)
    if not success and settings.GOOGLE_OAUTH_ERROR_REDIRECT_URL:
        query = urlencode({"google_calendar": "error", "reason": error or "oauth_failed"})
        return RedirectResponse(url=f"{settings.GOOGLE_OAUTH_ERROR_REDIRECT_URL}?{query}", status_code=302)
    if success:
        return GoogleOAuthCallbackOut(connected=True, google_account_email=email)
    raise HTTPException(status_code=400, detail=error or "Google OAuth failed")


@router.get("/status", response_model=GoogleCalendarConnectionStatusOut)
def get_google_calendar_status(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    connection = (
        db.query(GoogleCalendarConnection)
        .filter(GoogleCalendarConnection.user_id == current_user.id)
        .first()
    )
    if not connection:
        return GoogleCalendarConnectionStatusOut(connected=False, scopes=[])

    scopes = [scope for scope in (connection.scope or "").split() if scope.strip()]
    return GoogleCalendarConnectionStatusOut(
        connected=True,
        google_account_email=connection.google_account_email,
        scopes=scopes,
    )


@router.get("/calendars", response_model=list[GoogleCalendarListItemOut])
def list_google_calendars(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    _require_google_oauth_configured()
    connection = _get_connection_or_404(db=db, user_id=current_user.id)
    payload = _authorized_google_get(
        db=db,
        connection=connection,
        url=f"{GOOGLE_CALENDAR_LIST_URL}?maxResults=250&minAccessRole=reader",
    )
    items = payload.get("items", [])
    return [
        GoogleCalendarListItemOut(
            id=item["id"],
            summary=item.get("summaryOverride") or item.get("summary") or item["id"],
            primary=bool(item.get("primary")),
            selected=bool(item.get("selected", True)),
            access_role=item.get("accessRole"),
            time_zone=item.get("timeZone"),
        )
        for item in items
        if not item.get("deleted")
    ]


@router.get("/connect", response_model=GoogleOAuthConnectOut)
def build_google_calendar_connect_url(
    current_user: User = Depends(get_current_verified_user),
):
    _require_google_oauth_configured()
    state = _build_state_token(user_id=current_user.id)
    query = urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(_get_google_scopes()),
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": state,
        }
    )
    return GoogleOAuthConnectOut(authorization_url=f"{GOOGLE_AUTH_URL}?{query}")


@router.get("/availability", response_model=GoogleCalendarAvailabilityOut)
def get_google_calendar_availability(
    period_id: Optional[int] = Query(default=None),
    calendar_id: str = Query(default="primary"),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    _require_google_oauth_configured()
    connection = _get_connection_or_404(db=db, user_id=current_user.id)
    period = _get_period_for_user(db=db, current_user=current_user, period_id=period_id)
    return _build_availability_for_period(
        db=db,
        connection=connection,
        period=period,
        calendar_id=calendar_id,
    )

@router.get("/suggest-schedule", response_model=GoogleCalendarSuggestedScheduleOut)
def suggest_schedule_from_google_calendar(
    period_id: Optional[int] = Query(default=None),
    calendar_id: str = Query(default="primary"),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    _require_google_oauth_configured()
    connection = _get_connection_or_404(db=db, user_id=current_user.id)
    period = _get_period_for_user(db=db, current_user=current_user, period_id=period_id)
    availability = _build_availability_for_period(
        db=db,
        connection=connection,
        period=period,
        calendar_id=calendar_id,
    )
    return _build_suggested_schedule_from_availability(availability=availability)


@router.post("/apply-suggestion", response_model=GoogleCalendarSuggestedScheduleOut)
def apply_google_calendar_suggestion(
    period_id: Optional[int] = Query(default=None),
    calendar_id: str = Query(default="primary"),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    _require_google_oauth_configured()
    connection = _get_connection_or_404(db=db, user_id=current_user.id)
    period = _get_period_for_user(db=db, current_user=current_user, period_id=period_id)

    now = datetime.now(timezone.utc)
    deadline = period.deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if deadline < now:
        raise HTTPException(status_code=403, detail="Cannot apply Google Calendar suggestion after deadline")

    availability = _build_availability_for_period(
        db=db,
        connection=connection,
        period=period,
        calendar_id=calendar_id,
    )
    suggestion = _build_suggested_schedule_from_availability(availability=availability)

    db.query(ScheduleEntry).filter(
        ScheduleEntry.user_id == current_user.id,
        ScheduleEntry.period_id == period.id,
    ).delete()

    for day, payload in suggestion.days.items():
        db.add(
            ScheduleEntry(
                user_id=current_user.id,
                period_id=period.id,
                day=day,
                status=payload.status,
                meta=payload.meta.model_dump() if payload.meta is not None else None,
            )
        )

    db.commit()
    return suggestion


@router.get("/callback", response_model=GoogleOAuthCallbackOut)
def google_calendar_oauth_callback(
    code: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    _require_google_oauth_configured()

    if error:
        return _redirect_or_json(success=False, error=error)
    if not code or not state:
        return _redirect_or_json(success=False, error="missing_code_or_state")

    user_id = _decode_state_token(state)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return _redirect_or_json(success=False, error="user_not_found")

    token_data = _json_post(
        GOOGLE_TOKEN_URL,
        {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
    )

    access_token = token_data.get("access_token")
    if not access_token:
        return _redirect_or_json(success=False, error="missing_access_token")

    userinfo = _json_get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    google_account_email = userinfo.get("email")

    token_expires_at = None
    expires_in = token_data.get("expires_in")
    if expires_in is not None:
        try:
            token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        except (TypeError, ValueError):
            token_expires_at = None

    connection = (
        db.query(GoogleCalendarConnection)
        .filter(GoogleCalendarConnection.user_id == user.id)
        .first()
    )
    if not connection:
        connection = GoogleCalendarConnection(user_id=user.id, access_token=access_token)
        db.add(connection)

    connection.google_account_email = google_account_email
    connection.access_token = access_token
    connection.refresh_token = token_data.get("refresh_token") or connection.refresh_token
    connection.token_type = token_data.get("token_type")
    connection.scope = token_data.get("scope")
    connection.token_expires_at = token_expires_at
    db.commit()

    return _redirect_or_json(success=True, email=google_account_email)


@router.delete("/disconnect", status_code=204)
def disconnect_google_calendar(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    connection = (
        db.query(GoogleCalendarConnection)
        .filter(GoogleCalendarConnection.user_id == current_user.id)
        .first()
    )
    if connection:
        db.delete(connection)
        db.commit()
