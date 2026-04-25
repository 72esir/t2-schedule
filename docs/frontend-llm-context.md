# Frontend LLM Context

Use this file as context for generating frontend code against the current backend.

## Product roles

- Employee:
  - can register
  - can login
  - fills schedule for current alliance period
  - can declare remaining vacation days during registration
  - can see personal streak based on completed periods

- Manager:
  - login only
  - creates and closes periods for own alliance
  - sees employee lists and submission stats
  - reviews employee schedules
  - moderates employee vacation day declarations
  - can see streak leaderboard for alliance employees

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
- Autosave status based on `GET /schedules/me/state`
- Hours summary by day/week/period
- Validation warnings for weekly hours and work streak
- Personal streak widget via `GET /auth/me/streak`
- Suggested template prompt via `GET /templates/suggested/current`
- Apply suggested template via `POST /templates/suggested/current/apply`
- Google Calendar connection status via `GET /integrations/google/status`
- Google Calendar connect URL via `GET /integrations/google/connect`
- Google Calendar list via `GET /integrations/google/calendars`
- Google Calendar availability via `GET /integrations/google/availability`
- Google Calendar schedule suggestion via `GET /integrations/google/suggest-schedule`
- Google Calendar suggestion apply via `POST /integrations/google/apply-suggestion`
- Google Calendar disconnect via `DELETE /integrations/google/disconnect`

## Required manager screens

- Login
- Dashboard with current period stats
- Dashboard summary via `GET /manager/dashboard`
- Streak leaderboard via `GET /manager/streaks`
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
- `DELETE /manager/users/{user_id}/reject`

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
2. Review `current_days`, `proposed_days`, `changed_days`, and employee comment
3. Approve with `PUT /manager/schedule-change-requests/{id}/approve`
4. Reject with `PUT /manager/schedule-change-requests/{id}/reject`

Important:

- employee can send only one request per active period
- approving a request replaces the stored schedule with the proposed version

## Autosave flow

Recommended frontend behavior before deadline:

1. Load initial schedule via `GET /schedules/me/state`
2. Keep local edits in form state
3. Debounce calls to `PUT /schedules/me`
4. After a successful save, refresh `GET /schedules/me/state` or locally update the save indicator

Use `last_saved_at` to show:

- `Saving...`
- `Saved at 15:32`
- `Save failed`

## Google Calendar connection flow

Backend currently supports:

- checking whether Google Calendar is connected
- getting OAuth authorization URL
- listing available calendars
- loading busy intervals for a selected calendar and period
- handling OAuth callback
- disconnecting Google Calendar

Recommended frontend flow:

1. On employee dashboard call `GET /integrations/google/status`
2. If `connected=false`, show button `Connect Google Calendar`
3. On click call `GET /integrations/google/connect`
4. Redirect browser to returned `authorization_url`
5. After successful OAuth callback, backend either:
   - redirects to frontend success URL if configured in env
   - or returns JSON if redirect envs are not configured
6. After return to frontend refresh `GET /integrations/google/status`

Important:

- this still does not yet suggest schedules from calendar events
- but frontend can already:
  - choose a calendar
  - load busy intervals for current period
  - load deterministic suggested schedule
  - preview it
  - apply it to the current employee schedule

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

