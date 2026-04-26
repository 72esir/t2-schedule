# T2 Schedule Backend API

This document is intended for frontend implementation and for pasting into an LLM.
It reflects the current backend contract with only two roles:

- `manager`
- `user`

## Base URL

- Local without Docker: `http://localhost:8000`
- Docker Compose: `http://localhost:8000`

## Auth model

- Authentication is Bearer JWT.
- Send header: `Authorization: Bearer <token>`
- Public registration is only for employees.
- Public registration always creates a user with role `user`.
- Manager accounts are not created via public registration.

## Email notifications

Backend can send employee email notifications after manager creates a new period.

Required env for SMTP:

- `EMAIL_ENABLED`
- `EMAIL_FROM`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_USE_SSL`
- `FRONTEND_APP_URL`

Current behavior:

- when manager creates a period through `POST /periods`
- or through `POST /periods/from-template`
- backend sends a background email to verified employees of the same alliance
- employees without email or without verification are skipped

## Shared enums

### UserRole

```json
["manager", "user"]
```

### VacationDaysStatus

```json
["pending", "approved", "rejected", "adjusted"]
```

### Schedule day status

Frontend should use only:

```json
["shift", "split", "dayoff", "vacation"]
```

### Schedule payload contracts

`status=shift`

```json
{
  "status": "shift",
  "meta": {
    "shiftStart": "09:00",
    "shiftEnd": "18:00"
  }
}
```

Rules:

- both fields are required
- time format must be `HH:MM`
- `shiftStart < shiftEnd`

`status=split`

```json
{
  "status": "split",
  "meta": {
    "splitStart1": "09:00",
    "splitEnd1": "13:00",
    "splitStart2": "14:00",
    "splitEnd2": "18:00"
  }
}
```

Rules:

- all four fields are required
- all values must be `HH:MM`
- `splitStart1 < splitEnd1`
- `splitStart2 < splitEnd2`
- first interval must end before or exactly when second interval starts

`status=dayoff`

```json
{
  "status": "dayoff",
  "meta": null
}
```

`status=vacation`

```json
{
  "status": "vacation",
  "meta": null
}
```

## Authentication endpoints

### POST `/auth/register`

Registers an employee.

Request body:

```json
{
  "email": "employee@example.com",
  "password": "secret123",
  "external_id": "6505365461",
  "full_name": "Ivan Ivanov",
  "alliance": "Alliance 1",
  "category": "operator",
  "vacation_days_declared": 14
}
```

Notes:

- `role` is not accepted from frontend.
- Registered user always gets `role=user`.
- `vacation_days_declared` is optional.

Response:

```json
{
  "id": 1,
  "external_id": "6505365461",
  "full_name": "Ivan Ivanov",
  "alliance": "Alliance 1",
  "category": "operator",
  "email": "employee@example.com",
  "registered": true,
  "is_verified": false,
  "role": "user",
  "vacation_days_declared": 14,
  "vacation_days_approved": null,
  "vacation_days_status": "pending"
}
```

### POST `/auth/login`

OAuth2 password form endpoint.

Content type:

- `application/x-www-form-urlencoded`

Form fields:

- `username` = email
- `password`

Response:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

### GET `/auth/me`

Returns current authenticated user.

### GET `/auth/me/streak`

Returns current employee streak based on completed alliance periods.

Rules:

- only periods whose deadline has already passed are evaluated
- period counts as success if employee saved schedule before deadline
- any post-deadline schedule change request breaks streak for that period
- response also contains:
  - `bonus_balance`
  - `redeemable_sets`

### POST `/auth/me/streak/redeem`

Converts employee streak into internal bonus balance.

Current rule:

- every `5` streak points can be converted into `10` bonus points
- one request redeems exactly one set
- redeemed streak is subtracted from current streak

Response:

```json
{
  "converted_streak": 5,
  "awarded_bonus": 10,
  "bonus_balance": 20,
  "current_streak": 0,
  "redeemable_sets": 0
}
```

### POST `/auth/verify`

Verifies account using verification token.

Request:

```json
{
  "token": "verification-token"
}
```

## Google Calendar integration

These endpoints manage Google Calendar connection and can already read calendar availability for a period.
They still do not yet generate schedules from those intervals.

Required env:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`

Optional env:

- `GOOGLE_OAUTH_SUCCESS_REDIRECT_URL`
- `GOOGLE_OAUTH_ERROR_REDIRECT_URL`

Recommended scope:

```text
openid email https://www.googleapis.com/auth/calendar.readonly
```

### GET `/integrations/google/status`

Returns whether current verified employee already connected Google Calendar.

Response when disconnected:

```json
{
  "connected": false,
  "google_account_email": null,
  "scopes": []
}
```

Response when connected:

```json
{
  "connected": true,
  "google_account_email": "employee@gmail.com",
  "scopes": [
    "openid",
    "email",
    "https://www.googleapis.com/auth/calendar.readonly"
  ]
}
```

### GET `/integrations/google/connect`

Returns Google OAuth authorization URL for current verified employee.

Response:

```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
}
```

Frontend should redirect browser to this URL.

### GET `/integrations/google/calendars`

Returns available Google calendars for the connected employee.

Response:

```json
[
  {
    "id": "primary",
    "summary": "My calendar",
    "primary": true,
    "selected": true,
    "access_role": "owner",
    "time_zone": "Asia/Yekaterinburg"
  }
]
```

### GET `/integrations/google/availability`

Returns busy intervals from Google Calendar for the employee period.

Query params:

- `period_id` optional
- `calendar_id` optional, default `primary`

Behavior:

- if `period_id` is omitted, backend uses current active employee period
- if a Google event is all-day, day gets `all_day=true`
- timed events are grouped into `busy_intervals`

Response:

```json
{
  "period_id": 11,
  "calendar_id": "primary",
  "period_start": "2026-04-27",
  "period_end": "2026-05-03",
  "time_zone": "Asia/Yekaterinburg",
  "days": {
    "2026-04-27": {
      "all_day": false,
      "event_count": 2,
      "busy_intervals": [
        {
          "start": "2026-04-27T09:00:00Z",
          "end": "2026-04-27T10:00:00Z"
        }
      ]
    }
  }
}
```

### GET `/integrations/google/suggest-schedule`

Builds deterministic suggested schedule from Google Calendar availability.

Query params:

- `period_id` optional
- `calendar_id` optional, default `primary`

Current heuristic:

- all-day event -> `dayoff`
- free window `>= 8h` -> `shift`
- two free windows `>= 4h` each -> `split`
- one shorter free window `>= 4h` -> shorter `shift`
- otherwise -> `dayoff`

Response:

```json
{
  "period_id": 11,
  "calendar_id": "primary",
  "period_start": "2026-04-27",
  "period_end": "2026-05-03",
  "suggested_days_count": 5,
  "days": {
    "2026-04-27": {
      "status": "shift",
      "meta": {
        "shiftStart": "10:00",
        "shiftEnd": "18:00"
      }
    }
  }
}
```

### POST `/integrations/google/apply-suggestion`

Applies deterministic Google Calendar suggestion to the employee schedule.

Query params:

- `period_id` optional
- `calendar_id` optional, default `primary`

Rules:

- works only before period deadline
- replaces current schedule for that period

### GET `/integrations/google/callback`

Google OAuth callback endpoint.

Behavior:

- exchanges `code` for tokens
- stores Google connection for the employee
- if success/error redirect env vars are configured, redirects browser there
- otherwise returns JSON response

JSON success response:

```json
{
  "connected": true,
  "google_account_email": "employee@gmail.com"
}
```

### DELETE `/integrations/google/disconnect`

Deletes stored Google Calendar connection for current verified employee.

## Period endpoints

### GET `/periods/current`

Returns active period for current user's alliance.

Possible responses:

- active period object
- `null` if no alliance or no active period

### GET `/periods/templates`

Returns available backend period templates.

Auth required: yes
Roles: `manager`

Response:

```json
[
  {
    "type": "week",
    "label": "1 week",
    "description": "Creates a 7-day period starting from period_start.",
    "requires_period_end": false
  },
  {
    "type": "two_weeks",
    "label": "2 weeks",
    "description": "Creates a 14-day period starting from period_start.",
    "requires_period_end": false
  },
  {
    "type": "month",
    "label": "Calendar month",
    "description": "Creates a period from period_start to the last day of that month.",
    "requires_period_end": false
  },
  {
    "type": "custom",
    "label": "Custom range",
    "description": "Creates a period using explicit period_start and period_end.",
    "requires_period_end": true
  }
]
```

### POST `/periods`

Creates a new active period for current manager alliance.

Auth required: yes
Roles: `manager`

Request:

```json
{
  "period_start": "2026-05-01",
  "period_end": "2026-05-14",
  "deadline": "2026-04-30T18:00:00Z"
}
```

Notes:

- Alliance is taken from current user, not from request body.
- Previous active period in same alliance is closed automatically.
- If email notifications are enabled, verified employees of the alliance receive a background email with period dates, deadline, and frontend link.

### POST `/periods/from-template`

Creates a new active period for current manager alliance using a backend template preset.

Auth required: yes
Roles: `manager`

Request examples:

`week`

```json
{
  "template_type": "week",
  "period_start": "2026-05-01",
  "deadline": "2026-04-30T18:00:00Z"
}
```

`two_weeks`

```json
{
  "template_type": "two_weeks",
  "period_start": "2026-05-01",
  "deadline": "2026-04-30T18:00:00Z"
}
```

`month`

```json
{
  "template_type": "month",
  "period_start": "2026-05-01",
  "deadline": "2026-04-30T18:00:00Z"
}
```

`custom`

```json
{
  "template_type": "custom",
  "period_start": "2026-05-01",
  "period_end": "2026-05-20",
  "deadline": "2026-04-30T18:00:00Z"
}
```

Rules:

- `week` sets `period_end = period_start + 6 days`
- `two_weeks` sets `period_end = period_start + 13 days`
- `month` sets `period_end` to the last day of the month of `period_start`
- `custom` requires explicit `period_end`
- For non-`custom` templates, `period_end` must not be sent
- Alliance is taken from current user, not from request body
- Previous active period in same alliance is closed automatically
- If email notifications are enabled, verified employees of the alliance receive a background email with period dates, deadline, and frontend link.

### POST `/periods/{period_id}/close`

Closes a period.

Auth required: yes
Roles: `manager`

### GET `/periods/current/stats`

Returns aggregate stats for current alliance period.

### GET `/periods/current/submissions`

Returns who submitted and who did not.

### GET `/periods/history`

Returns all periods of current alliance.

## Schedule endpoints

### GET `/schedules/me`

Returns current user's schedule for active alliance period.

Auth required: yes
Role: verified user

### GET `/schedules/me/state`

Returns current user's schedule plus autosave metadata for the active alliance period.

Auth required: yes
Role: verified user

Response:

```json
{
  "days": {
    "2026-05-01": {
      "status": "shift",
      "meta": {
        "shiftStart": "09:00",
        "shiftEnd": "18:00"
      }
    }
  },
  "last_saved_at": "2026-04-25T15:32:11Z"
}
```

Notes:

- `last_saved_at` is `null` when the user has no saved schedule for the active period
- frontend can use this endpoint for autosave UI like `Saved at 15:32`

### PUT `/schedules/me`

Replaces current user's schedule for active alliance period.

Auth required: yes
Role: verified user

Request:

```json
{
  "days": {
    "2026-05-01": {
      "status": "shift",
      "meta": {
        "shiftStart": "09:00",
        "shiftEnd": "18:00"
      }
    },
    "2026-05-02": {
      "status": "dayoff",
      "meta": null
    }
  }
}
```

Deadline rule:

- Employee can update schedule only until the active period `deadline`.
- If deadline has passed, backend returns `403`.

### POST `/schedules/change-request`

Creates one post-deadline schedule review request for the current active period.

Auth required: yes
Role: verified user

Rules:

- available only after the current period deadline
- one employee can create only one request per current period
- request stores a proposed new version of the schedule
- manager later approves or rejects this request

Request:

```json
{
  "employee_comment": "Need to correct late shift changes",
  "days": {
    "2026-05-01": {
      "status": "shift",
      "meta": {
        "shiftStart": "10:00",
        "shiftEnd": "19:00"
      }
    }
  }
}
```

### GET `/schedules/change-request/me`

Returns current employee request for the active period, if it exists.

Possible responses:

- request object
- `null` if no request exists

### GET `/schedules/by-user/{user_id}`

Returns one employee schedule for manager review.

Auth required: yes
Roles: `manager`

Notes:

- Manager can only access users from same alliance.
- Current period is resolved by that employee's alliance.

### GET `/schedules/me/summary`

Returns calculated hour summary for current user's active alliance period.

Auth required: yes
Role: verified user

Response:

```json
{
  "daily_hours": {
    "2026-05-01": 8.0,
    "2026-05-02": 0.0
  },
  "weekly_hours": {
    "2026-04-27": 40.0
  },
  "period_total_hours": 80.0,
  "vacation_days_count": 2,
  "max_work_streak": 5
}
```

### GET `/schedules/by-user/{user_id}/summary`

Returns calculated hour summary for one employee in manager review mode.

Auth required: yes
Roles: `manager`

### GET `/schedules/me/validation`

Returns business-rule validation for current user's active period.

Auth required: yes
Role: verified user

Rules currently checked:

- target `40` hours per week
- not more than `6` work days in a row

Response:

```json
{
  "is_valid": false,
  "violations": [
    {
      "code": "WEEKLY_HOURS_UNDER",
      "level": "warning",
      "message": "Недобор часов за неделю, начиная с 2026-04-27",
      "context": {
        "week_start": "2026-04-27",
        "actual_hours": 36.0,
        "required_hours": 40,
        "difference": 4.0
      }
    }
  ],
  "summary": {
    "daily_hours": {
      "2026-05-01": 8.0
    },
    "weekly_hours": {
      "2026-04-27": 36.0
    },
    "period_total_hours": 36.0,
    "vacation_days_count": 0,
    "max_work_streak": 4
  }
}
```

### GET `/schedules/by-user/{user_id}/validation`

Returns business-rule validation for one employee in manager review mode.

Auth required: yes
Roles: `manager`

## Manager endpoints

### GET `/manager/dashboard`

Returns one aggregated dashboard payload for current manager alliance.

Auth required: yes
Roles: `manager`

Response:

```json
{
  "current_period": {
    "id": 3,
    "alliance": "Alliance 1",
    "period_start": "2026-05-01",
    "period_end": "2026-05-14",
    "deadline": "2026-04-30T18:00:00Z",
    "is_open": true,
    "created_at": "2026-04-25T10:00:00Z",
    "updated_at": "2026-04-25T10:00:00Z"
  },
  "total_employees": 45,
  "submitted_count": 30,
  "pending_count": 15,
  "pending_verification_count": 4,
  "pending_vacation_moderation_count": 6,
  "pending_schedule_change_requests_count": 3,
  "employees_with_violations_count": 5,
  "problem_employees": [
    {
      "user_id": 12,
      "full_name": "Ivan Ivanov",
      "email": "ivan@example.com",
      "violation_count": 2,
      "violation_codes": ["WEEKLY_HOURS_UNDER", "WORK_STREAK_OVER_6"],
      "summary": {
        "daily_hours": {
          "2026-05-01": 8.0
        },
        "weekly_hours": {
          "2026-04-27": 36.0
        },
        "period_total_hours": 36.0,
        "vacation_days_count": 0,
        "max_work_streak": 7
      }
    }
  ]
}
```

Notes:

- `current_period` can be `null` if there is no active period
- `pending_count` is based on verified employees who have not submitted schedule entries in the active period
- `pending_schedule_change_requests_count` is the number of unresolved post-deadline review requests
- `problem_employees` includes only employees from the current alliance who already have schedule entries and at least one validation violation

### GET `/manager/schedule-change-requests/pending`

Returns pending post-deadline schedule review requests for the current manager alliance.
Each item contains:
- `current_days` - current saved schedule in the period
- `proposed_days` - employee proposed replacement schedule
- `changed_days` - dates where current and proposed schedule differ

Auth required: yes
Roles: `manager`

### PUT `/manager/schedule-change-requests/{request_id}/approve`

Approves a post-deadline request and replaces the employee schedule with the proposed version.

Auth required: yes
Roles: `manager`

Request:

```json
{
  "manager_comment": "Approved after review"
}
```

### PUT `/manager/schedule-change-requests/{request_id}/reject`

Rejects a post-deadline request without changing the stored schedule.

Auth required: yes
Roles: `manager`

Request:

```json
{
  "manager_comment": "Rejected, changes conflict with staffing plan"
}
```

### GET `/manager/users`

Returns users visible to current manager.

Auth required: yes
Roles: `manager`

Query params:

- `verified=true|false`
- `alliance=<string>`
- `role=manager|user`
- `vacation_days_status=pending|approved|rejected|adjusted`

Behavior:

- If manager does not pass `alliance`, backend automatically restricts to manager's alliance.

### GET `/manager/streaks`

Returns streak leaderboard for verified employees in current manager alliance.

### GET `/templates/suggested/current`

Returns a suggested schedule template for current active period if the employee filled at least 2 closed periods with the exact same pattern.

Notes:

- only exact matches are considered
- only closed periods with the same duration as current active period are compared
- if no suggestion is found, `has_suggestion=false`

### POST `/templates/suggested/current/apply`

Applies the current suggested template to the active period.

### GET `/manager/vacation-days/pending`

Returns only employees from current manager alliance whose declared vacation days still require moderation.

Auth required: yes
Roles: `manager`

Response:

```json
[
  {
    "id": 12,
    "external_id": "6505365461",
    "full_name": "Ivan Ivanov",
    "alliance": "Alliance 1",
    "category": "operator",
    "email": "employee@example.com",
    "registered": true,
    "is_verified": false,
    "role": "user",
    "vacation_days_declared": 14,
    "vacation_days_approved": null,
    "vacation_days_status": "pending"
  }
]
```

### GET `/manager/users/pending-verification`

Returns only employees from current manager alliance whose accounts are not yet verified.

Auth required: yes
Roles: `manager`

Response:

```json
[
  {
    "id": 8,
    "external_id": "6505000001",
    "full_name": "Petr Petrov",
    "alliance": "Alliance 1",
    "category": "operator",
    "email": "petr@example.com",
    "registered": true,
    "is_verified": false,
    "role": "user",
    "vacation_days_declared": 21,
    "vacation_days_approved": null,
    "vacation_days_status": "pending"
  }
]
```

### PUT `/manager/users/{user_id}/verify`

Marks user as verified.

### DELETE `/manager/users/{user_id}/reject`

Deletes a non-verified employee from current manager alliance.

### PUT `/manager/users/{user_id}/vacation-days`

Moderates employee vacation days.

Auth required: yes
Roles: `manager`

Request:

```json
{
  "approved_days": 12,
  "status": "adjusted"
}
```

Behavior:

- `approved` -> set approved days and status
- `adjusted` -> set approved days and status
- `rejected` -> clear approved days and set status

## Template endpoints

### GET `/templates`

Returns current user's templates.

### POST `/templates`

Creates a template.

### DELETE `/templates/{template_id}`

Deletes current user's template.

## Export endpoint

### GET `/export/schedule`

Exports current alliance period to Excel.

Auth required: yes
Roles: `manager`

Query params:

- optional `period_id`

Response:

- binary `.xlsx` file

Workbook contents:

- `Schedule` sheet:
  - one row per employee
  - total hours
  - vacation days count
  - violation codes
  - one column per day of the selected period
- `Summary` sheet:
  - one row per employee
  - submitted or not
  - total hours
  - vacation days count
  - max work streak
  - weekly hours summary
  - violation count and codes

Notes:

- only verified employees from the current manager alliance are exported
- rows with validation violations are highlighted

## Frontend integration notes

- After login always call `/auth/me`.
- Use returned `role` to decide which UI to show.
- Employee UI:
  - login
  - register
  - current period
  - own schedule
- Manager UI:
  - login only
  - current period management
  - employee list
  - pending employee verification queue
  - submission stats
  - employee schedule review
  - pending vacation moderation queue
  - vacation days moderation
