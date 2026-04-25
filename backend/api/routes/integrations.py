import json
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.core import get_current_verified_user
from backend.core.config import settings
from backend.db import get_db
from backend.models import GoogleCalendarConnection, User
from backend.schemas import (
    GoogleCalendarConnectionStatusOut,
    GoogleOAuthCallbackOut,
    GoogleOAuthConnectOut,
)

router = APIRouter(prefix="/integrations/google", tags=["integrations"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_STATE_TTL_MINUTES = 10


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
        raise HTTPException(status_code=502, detail=f"Google user info request failed: {detail}") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail="Google user info request failed") from exc


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
