# Frontend LLM Context

Use this file as context for generating frontend code against the current backend.

## Product roles

- Employee:
  - can register
  - can login
  - fills schedule for current alliance period
  - can declare remaining vacation days during registration

- Manager:
  - login only
  - creates and closes periods for own alliance
  - sees employee lists and submission stats
  - reviews employee schedules
  - moderates employee vacation day declarations

- Admin:
  - technical superuser
  - broader user-management abilities

## UI entry flow

- Start screen should let user choose:
  - `I am a manager`
  - `I am an employee`
- If manager selected:
  - show login form only
- If employee selected:
  - show login and registration options

## Registration flow

Employee registration fields:

- `email`
- `password`
- `external_id` optional
- `full_name` optional
- `alliance` optional now, but backend supports it
- `category` optional
- `vacation_days_declared` optional integer

Important:

- Frontend must not send role during registration.
- Backend will always create `role=user`.

## Required employee screens

- Login
- Registration
- Current period info
- Schedule calendar for active period
- Save/update schedule
- Read-only empty state if no active period exists

## Required manager screens

- Login
- Dashboard with current period stats
- Create period
- Close period
- Employee list
- Submission status list
- Employee details and schedule review
- Vacation moderation controls

## Vacation moderation UI

For each employee show:

- declared vacation days
- approved vacation days
- moderation status

Manager actions:

- approve
- reject
- adjust with corrected number

## API reference

Use `docs/backend-api.md` as the source of truth for requests and responses.

