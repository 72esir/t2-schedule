# T2 Schedule Backend API

This document is intended for frontend implementation and for pasting into an LLM.
All endpoints below are backend-facing contracts for the current state of the project.

## Base URL

- Local without Docker: `http://localhost:8000`
- Docker Compose: `http://localhost:8000`

## Auth model

- Authentication is Bearer JWT.
- Send header: `Authorization: Bearer <token>`
- Public registration is only for employees.
- Public registration always creates a user with role `user`.
- Roles returned by backend:
  - `admin`
  - `manager`
  - `user`

## Main business rules

- Periods are scoped by `alliance`.
- A user only sees the active period of their own `alliance`.
- A manager can only work with users from their own `alliance`.
- Employee registration can include declared remaining vacation days.
- Manager/admin can later approve, reject, or adjust vacation days.

## Shared enums

### UserRole

```json
["admin", "manager", "user"]
```

### VacationDaysStatus

```json
["pending", "approved", "rejected", "adjusted"]
```

### Schedule day status

Current backend accepts free-form strings, but frontend should use only:

```json
["shift", "split", "dayoff", "vacation"]
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

Auth required: yes

Response shape is the same as registration response.

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

Auth required: yes

Possible responses:

- active period object
- `null` if no alliance or no active period

Response:

```json
{
  "id": 10,
  "alliance": "Alliance 1",
  "period_start": "2026-05-01",
  "period_end": "2026-05-14",
  "deadline": "2026-04-30T18:00:00Z",
  "is_open": true,
  "created_at": "2026-04-25T10:00:00Z",
  "updated_at": "2026-04-25T10:00:00Z"
}
```

### POST `/periods`

Creates a new active period for current manager/admin alliance.

Auth required: yes
Roles: `manager`, `admin`

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

### POST `/periods/{period_id}/close`

Closes a period.

Auth required: yes
Roles: `manager`, `admin`

### GET `/periods/current/stats`

Returns aggregate stats for current alliance period.

Response:

```json
{
  "total_employees": 45,
  "submitted_count": 20,
  "pending_count": 25
}
```

### GET `/periods/current/submissions`

Returns who submitted and who did not.

Response:

```json
{
  "submitted": [
    {
      "id": 1,
      "full_name": "Ivan Ivanov",
      "email": "employee@example.com",
      "alliance": "Alliance 1"
    }
  ],
  "pending": []
}
```

### GET `/periods/history`

Returns all periods of current alliance.

## Schedule endpoints

### GET `/schedules/me`

Returns current user's schedule for active alliance period.

Auth required: yes
Role: verified user

Response:

```json
{
  "2026-05-01": {
    "status": "shift",
    "meta": {
      "shiftStart": "09:00",
      "shiftEnd": "18:00"
    }
  }
}
```

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

Notes:

- Only dates inside current active period are allowed.
- Backend currently replaces all stored entries for this user/period with the submitted payload.

### GET `/schedules/by-user/{user_id}`

Returns one employee schedule for manager/admin review.

Auth required: yes
Roles: `manager`, `admin`

Notes:

- Manager can only access users from same alliance.
- Current period is resolved by that employee's alliance.

Response:

```json
{
  "user": {
    "id": 1,
    "external_id": "6505365461",
    "full_name": "Ivan Ivanov",
    "alliance": "Alliance 1",
    "category": "operator",
    "email": "employee@example.com",
    "registered": true,
    "is_verified": true,
    "role": "user",
    "vacation_days_declared": 14,
    "vacation_days_approved": 12,
    "vacation_days_status": "adjusted"
  },
  "entries": {
    "2026-05-01": {
      "status": "shift",
      "meta": {
        "shiftStart": "09:00",
        "shiftEnd": "18:00"
      }
    }
  },
  "vacation_work": null
}
```

## Admin / manager endpoints

### GET `/admin/users`

Returns users visible to current admin/manager.

Auth required: yes
Roles: `manager`, `admin`

Query params:

- `verified=true|false`
- `alliance=<string>`
- `role=admin|manager|user`
- `vacation_days_status=pending|approved|rejected|adjusted`

Manager behavior:

- If manager does not pass `alliance`, backend automatically restricts to manager's alliance.

### PUT `/admin/users/{user_id}/verify`

Marks user as verified.

### DELETE `/admin/users/{user_id}`

Deletes user.

### PUT `/admin/users/{user_id}/role`

Changes user role.

Current backend expects `new_role` as query parameter.

Example:

`PUT /admin/users/5/role?new_role=manager`

### PUT `/admin/users/{user_id}/alliance`

Changes user alliance.

Current backend expects `new_alliance` as query parameter.

Example:

`PUT /admin/users/5/alliance?new_alliance=Alliance%202`

### PUT `/admin/users/{user_id}/vacation-days`

Moderates employee vacation days.

Auth required: yes
Roles: `manager`, `admin`

Manager can only moderate employees from same alliance.

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

Request:

```json
{
  "name": "5/2 09:00-18:00",
  "work_days": 5,
  "rest_days": 2,
  "shift_start": "09:00",
  "shift_end": "18:00",
  "has_break": false,
  "break_start": null,
  "break_end": null
}
```

### DELETE `/templates/{template_id}`

Deletes current user's template.

## Export endpoint

### GET `/export/schedule`

Exports current alliance period to Excel.

Auth required: yes
Roles: `manager`, `admin`

Query params:

- optional `period_id`

Response:

- binary `.xlsx` file

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
  - submission stats
  - employee schedule review
  - vacation days moderation

