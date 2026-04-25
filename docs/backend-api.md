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

### GET `/schedules/by-user/{user_id}`

Returns one employee schedule for manager review.

Auth required: yes
Roles: `manager`

Notes:

- Manager can only access users from same alliance.
- Current period is resolved by that employee's alliance.

## Manager endpoints

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
