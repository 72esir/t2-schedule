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

### POST `/auth/verify`

Verifies account using verification token.

Request:

```json
{
  "token": "verification-token"
}
```

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
