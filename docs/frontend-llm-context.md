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
- Read-only state after deadline
- Post-deadline schedule change request form
- View own post-deadline request status
- Hours summary by day/week/period
- Validation warnings for weekly hours and work streak

## Required manager screens

- Login
- Dashboard with current period stats
- Dashboard summary via `GET /manager/dashboard`
- Create period
- Create period from template: `week`, `two_weeks`, `month`, `custom`
- Close period
- Employee list
- Pending employee verification queue
- Submission status list
- Employee details and schedule review
- Employee hour summary
- Employee validation warnings
- Pending vacation moderation queue
- Vacation moderation controls
- Pending post-deadline schedule review requests
- Excel export with hours and violations

## Vacation moderation UI

For each employee show:

- declared vacation days
- approved vacation days
- moderation status

Manager actions:

- approve
- reject
- adjust with corrected number

Recommended API for that screen:

- `GET /manager/vacation-days/pending`
- `PUT /manager/users/{user_id}/vacation-days`

## Account verification UI

Manager should also have a queue of employees waiting for account verification.

Recommended API for that screen:

- `GET /manager/users/pending-verification`
- `PUT /manager/users/{user_id}/verify`

## Manager dashboard UI

Recommended main query for the manager home screen:

- `GET /manager/dashboard`

It already returns:

- current active period
- total employees
- submitted vs pending counts
- pending verification count
- pending vacation moderation count
- pending schedule change requests count
- problem employees with validation violations

Frontend can use this single response for dashboard cards and a "problem schedules" block.

## Post-deadline review flow

Employee flow:

1. After deadline, normal `PUT /schedules/me` is blocked.
2. Employee edits a proposed version locally in UI.
3. Employee sends it to `POST /schedules/change-request`.
4. Employee can check current request status with `GET /schedules/change-request/me`.

Manager flow:

1. Open queue from `GET /manager/schedule-change-requests/pending`
2. Review proposed days and employee comment
3. Approve with `PUT /manager/schedule-change-requests/{id}/approve`
4. Reject with `PUT /manager/schedule-change-requests/{id}/reject`

Important:

- employee can send only one request per active period
- approving a request replaces the stored schedule with the proposed version

## API reference

Use `docs/backend-api.md` as the source of truth for requests and responses.

## Period template flow

Manager period creation should support two modes:

- manual range via `POST /periods`
- template-based creation via `POST /periods/from-template`

Recommended frontend flow:

1. Call `GET /periods/templates`
2. Show template cards or radio buttons
3. Collect:
   - `period_start`
   - `deadline`
   - `period_end` only when template is `custom`
4. Send selected template payload to `POST /periods/from-template`

