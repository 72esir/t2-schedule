from __future__ import annotations

import json
import os
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.auth import get_password_hash
from backend.db import SessionLocal
from backend.models import CollectionPeriod, ScheduleEntry, ScheduleTemplate, User, UserRole, VerificationToken

BASE_URL = os.getenv("SMOKE_BASE_URL", "http://localhost:8000").rstrip("/")
REQUEST_TIMEOUT = float(os.getenv("SMOKE_TIMEOUT_SECONDS", "20"))
KEEP_DATA = os.getenv("SMOKE_KEEP_DATA", "").lower() in {"1", "true", "yes"}


class SmokeFailure(RuntimeError):
    pass


def log(message: str) -> None:
    print(f"[smoke] {message}")


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


class HttpClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def request_json(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        json_body: dict[str, Any] | None = None,
        form_body: dict[str, Any] | None = None,
    ) -> Any:
        body: bytes | None = None
        headers: dict[str, str] = {}

        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif form_body is not None:
            body = parse.urlencode(form_body).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        if token:
            headers["Authorization"] = f"Bearer {token}"

        req = request.Request(f"{self.base_url}{path}", data=body, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                raw = response.read()
                if response.status == 204 or not raw:
                    return None
                return json.loads(raw.decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SmokeFailure(f"{method} {path} failed with {exc.code}: {detail}") from exc

    def request_binary(self, method: str, path: str, *, token: str | None = None) -> bytes:
        headers: dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = request.Request(f"{self.base_url}{path}", headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                return response.read()
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SmokeFailure(f"{method} {path} failed with {exc.code}: {detail}") from exc


@contextmanager
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def wait_for_api() -> None:
    deadline = time.time() + 60
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with request.urlopen(f"{BASE_URL}/health", timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
                if payload.get("status") == "ok":
                    log(f"API is up at {BASE_URL}")
                    return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(2)

    raise SmokeFailure(f"API did not become healthy at {BASE_URL}: {last_error}")


def create_manager(email: str, password: str, alliance: str) -> int:
    with db_session() as session:
        manager = User(
            email=email,
            password_hash=get_password_hash(password),
            registered=True,
            is_verified=True,
            full_name="Smoke Manager",
            alliance=alliance,
            category="manager",
            role=UserRole.MANAGER,
        )
        session.add(manager)
        session.commit()
        session.refresh(manager)
        return manager.id


def get_verification_token(user_email: str) -> str:
    with db_session() as session:
        token = (
            session.query(VerificationToken)
            .join(User)
            .filter(User.email == user_email, VerificationToken.consumed.is_(False))
            .order_by(VerificationToken.created_at.desc())
            .first()
        )
        expect(token is not None, f"verification token not found for {user_email}")
        return token.token


def cleanup_test_data(emails: list[str], alliance: str) -> None:
    with db_session() as session:
        users = session.query(User).filter(User.email.in_(emails)).all()
        user_ids = [user.id for user in users]

        if user_ids:
            session.query(ScheduleEntry).filter(ScheduleEntry.user_id.in_(user_ids)).delete(
                synchronize_session=False
            )
            session.query(ScheduleTemplate).filter(ScheduleTemplate.user_id.in_(user_ids)).delete(
                synchronize_session=False
            )
            session.query(VerificationToken).filter(VerificationToken.user_id.in_(user_ids)).delete(
                synchronize_session=False
            )
            session.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)

        session.query(ScheduleEntry).filter(
            ScheduleEntry.period_id.in_(
                session.query(CollectionPeriod.id).filter(CollectionPeriod.alliance == alliance)
            )
        ).delete(synchronize_session=False)
        session.query(CollectionPeriod).filter(CollectionPeriod.alliance == alliance).delete(
            synchronize_session=False
        )
        session.commit()


def build_schedule_days(period_start: str) -> dict[str, Any]:
    start = date.fromisoformat(period_start)
    days: dict[str, Any] = {}
    for offset in range(7):
        current_day = (start + timedelta(days=offset)).isoformat()
        days[current_day] = {
            "status": "shift",
            "meta": {
                "shiftStart": "09:00",
                "shiftEnd": "17:00",
            },
        }
    return days


def next_monday(start_day: date) -> date:
    days_ahead = (7 - start_day.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return start_day + timedelta(days=days_ahead)


def main() -> int:
    suffix = uuid.uuid4().hex[:8]
    alliance = f"Smoke Alliance {suffix}"
    manager_email = f"smoke-manager-{suffix}@example.com"
    employee_email = f"smoke-employee-{suffix}@example.com"
    pending_email = f"smoke-pending-{suffix}@example.com"
    manager_password = "SmokePass123!"
    employee_password = "SmokePass123!"
    created_emails = [manager_email, employee_email, pending_email]

    client = HttpClient(BASE_URL)

    try:
        wait_for_api()

        log("creating test manager in database")
        create_manager(manager_email, manager_password, alliance)

        log("logging in manager")
        manager_login = client.request_json(
            "POST",
            "/auth/login",
            form_body={"username": manager_email, "password": manager_password},
        )
        manager_token = manager_login["access_token"]

        log("registering verified-path employee")
        employee_register = client.request_json(
            "POST",
            "/auth/register",
            json_body={
                "email": employee_email,
                "password": employee_password,
                "external_id": f"emp-{suffix}-1",
                "full_name": "Smoke Employee",
                "alliance": alliance,
                "category": "operator",
                "vacation_days_declared": 14,
            },
        )
        employee_id = employee_register["id"]
        expect(employee_register["role"] == "user", "employee registration should create role=user")

        log("verifying first employee through auth token flow")
        verification_token = get_verification_token(employee_email)
        verify_response = client.request_json(
            "POST",
            "/auth/verify",
            json_body={"token": verification_token},
        )
        expect(verify_response["is_verified"] is True, "auth verify should mark employee as verified")

        log("registering second employee for manager moderation flow")
        pending_register = client.request_json(
            "POST",
            "/auth/register",
            json_body={
                "email": pending_email,
                "password": employee_password,
                "external_id": f"emp-{suffix}-2",
                "full_name": "Pending Employee",
                "alliance": alliance,
                "category": "operator",
                "vacation_days_declared": 21,
            },
        )
        pending_employee_id = pending_register["id"]

        log("checking manager moderation queues")
        pending_verification = client.request_json(
            "GET",
            "/manager/users/pending-verification",
            token=manager_token,
        )
        expect(
            any(user["id"] == pending_employee_id for user in pending_verification),
            "pending verification queue should include second employee",
        )

        pending_vacation = client.request_json(
            "GET",
            "/manager/vacation-days/pending",
            token=manager_token,
        )
        expect(
            any(user["id"] == pending_employee_id for user in pending_vacation),
            "pending vacation queue should include second employee",
        )

        log("moderating vacation days and verifying second employee via manager endpoints")
        moderated_user = client.request_json(
            "PUT",
            f"/manager/users/{pending_employee_id}/vacation-days",
            token=manager_token,
            json_body={"approved_days": 18, "status": "adjusted"},
        )
        expect(moderated_user["vacation_days_approved"] == 18, "vacation moderation should update approved days")

        verified_by_manager = client.request_json(
            "PUT",
            f"/manager/users/{pending_employee_id}/verify",
            token=manager_token,
        )
        expect(verified_by_manager["is_verified"] is True, "manager verify should mark second employee as verified")

        log("creating a manual period and closing it")
        today = datetime.now(timezone.utc).date()
        manual_start = next_monday(today) + timedelta(days=7)
        manual_end = manual_start + timedelta(days=2)
        manual_deadline = datetime.combine(today + timedelta(days=6), dt_time(hour=18), tzinfo=timezone.utc)
        manual_period = client.request_json(
            "POST",
            "/periods",
            token=manager_token,
            json_body={
                "period_start": manual_start.isoformat(),
                "period_end": manual_end.isoformat(),
                "deadline": manual_deadline.isoformat().replace("+00:00", "Z"),
            },
        )
        client.request_json("POST", f"/periods/{manual_period['id']}/close", token=manager_token)

        log("creating an active week period from template")
        active_start = next_monday(today) + timedelta(days=14)
        active_deadline = datetime.combine(today + timedelta(days=13), dt_time(hour=18), tzinfo=timezone.utc)
        period_templates = client.request_json("GET", "/periods/templates", token=manager_token)
        expect(any(template["type"] == "week" for template in period_templates), "week period template should exist")

        active_period = client.request_json(
            "POST",
            "/periods/from-template",
            token=manager_token,
            json_body={
                "template_type": "week",
                "period_start": active_start.isoformat(),
                "deadline": active_deadline.isoformat().replace("+00:00", "Z"),
            },
        )
        expect(active_period["is_open"] is True, "template-created period should be open")

        current_period = client.request_json("GET", "/periods/current", token=manager_token)
        expect(current_period["id"] == active_period["id"], "current period should match active template period")

        history = client.request_json("GET", "/periods/history", token=manager_token)
        expect(len(history) >= 2, "period history should include manual and template periods")

        log("logging in verified employee and checking auth/me")
        employee_login = client.request_json(
            "POST",
            "/auth/login",
            form_body={"username": employee_email, "password": employee_password},
        )
        employee_token = employee_login["access_token"]
        me = client.request_json("GET", "/auth/me", token=employee_token)
        expect(me["id"] == employee_id, "auth/me should return the verified employee")

        log("creating, listing, and deleting employee schedule template")
        schedule_template = client.request_json(
            "POST",
            "/templates",
            token=employee_token,
            json_body={
                "name": "5/2 Morning",
                "work_days": 5,
                "rest_days": 2,
                "shift_start": "09:00",
                "shift_end": "18:00",
                "has_break": False,
                "break_start": None,
                "break_end": None,
            },
        )
        template_list = client.request_json("GET", "/templates", token=employee_token)
        expect(any(item["id"] == schedule_template["id"] for item in template_list), "template list should include new template")
        client.request_json("DELETE", f"/templates/{schedule_template['id']}", token=employee_token)

        log("submitting schedule and checking hours and violations")
        schedule_payload = {"days": build_schedule_days(active_period["period_start"])}
        updated_schedule = client.request_json("PUT", "/schedules/me", token=employee_token, json_body=schedule_payload)
        expect(len(updated_schedule) == 7, "schedule update should store 7 days")

        my_schedule = client.request_json("GET", "/schedules/me", token=employee_token)
        expect(len(my_schedule) == 7, "employee schedule should return 7 days")

        my_summary = client.request_json("GET", "/schedules/me/summary", token=employee_token)
        expect(my_summary["period_total_hours"] == 56.0, "7x8h schedule should total 56 hours")

        my_validation = client.request_json("GET", "/schedules/me/validation", token=employee_token)
        violation_codes = {item["code"] for item in my_validation["violations"]}
        expect("WEEKLY_HOURS_OVER" in violation_codes, "validation should flag weekly hours overflow")
        expect("WORK_STREAK_OVER_6" in violation_codes, "validation should flag work streak overflow")

        log("checking manager review endpoints")
        review_schedule = client.request_json("GET", f"/schedules/by-user/{employee_id}", token=manager_token)
        expect(str(employee_id) == str(review_schedule["user"]["id"]), "manager review should return selected employee")

        review_summary = client.request_json("GET", f"/schedules/by-user/{employee_id}/summary", token=manager_token)
        expect(review_summary["period_total_hours"] == 56.0, "manager summary should match employee summary")

        review_validation = client.request_json("GET", f"/schedules/by-user/{employee_id}/validation", token=manager_token)
        expect(len(review_validation["violations"]) >= 2, "manager validation should expose employee violations")

        log("checking period stats, submissions, dashboard, and export")
        stats = client.request_json("GET", "/periods/current/stats", token=manager_token)
        expect(stats["submitted_count"] >= 1, "stats should show at least one submitted employee")

        submissions = client.request_json("GET", "/periods/current/submissions", token=manager_token)
        expect(
            any(user["id"] == employee_id for user in submissions["submitted"]),
            "submitted list should include the employee with a schedule",
        )

        dashboard = client.request_json("GET", "/manager/dashboard", token=manager_token)
        expect(dashboard["current_period"]["id"] == active_period["id"], "dashboard should point to active period")
        expect(dashboard["employees_with_violations_count"] >= 1, "dashboard should include problem employees")

        export_bytes = client.request_binary("GET", "/export/schedule", token=manager_token)
        expect(len(export_bytes) > 1024, "exported xlsx should not be empty")
        expect(export_bytes[:2] == b"PK", "xlsx should be a zip-based workbook")

        log("smoke test passed")
        return 0
    finally:
        if KEEP_DATA:
            log("SMOKE_KEEP_DATA is enabled, skipping cleanup")
        else:
            log("cleaning up smoke test data")
            cleanup_test_data(created_emails, alliance)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SmokeFailure as exc:
        log(f"FAILED: {exc}")
        raise SystemExit(1) from exc
