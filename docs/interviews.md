# Interview Management

Interviews belong to an application and represent one hiring round: Aptitude, Technical, Managerial, or HR. Each has an assigned active interviewer, timezone-aware scheduled time, duration, status, result, and optional feedback.

## Access and workflow

- ADMIN can list all interviews, schedule an interview for a shortlisted application, assign an interviewer, reschedule, or cancel.
- INTERVIEWER can only list and open interviews assigned to their account. They can submit PASSED or FAILED plus feedback while the interview is active; that completes the interview.
- STUDENT can only list and view interviews attached to their own applications. Their response contains the schedule, round, and status, without interviewer feedback or candidate-only fields.
- Other roles are denied. Unauthorized interview details return 404 to avoid exposing whether another user’s interview exists.
- New schedules and reschedules must be in the future and include a timezone. Durations are limited to 15–240 minutes. An interviewer cannot be double-booked for overlapping active interviews.
- Rescheduling updates the current scheduled time and sets RESCHEDULED. Completed and cancelled interviews cannot be rescheduled; completed interviews cannot be cancelled.

## API

| Method | Endpoint | Access |
| --- | --- | --- |
| GET | `/api/interviews` | ADMIN, INTERVIEWER (assigned only), STUDENT (own applications only) |
| GET | `/api/interviews/{id}` | Same scoped access |
| GET | `/api/interviews/interviewers` | ADMIN |
| POST | `/api/interviews` | ADMIN |
| PATCH | `/api/interviews/{id}/reschedule` | ADMIN |
| POST | `/api/interviews/{id}/cancel` | ADMIN |
| PATCH | `/api/interviews/{id}/result` | Assigned INTERVIEWER |

## Storage

`interviews.round_name` is constrained to `aptitude`, `technical`, `managerial`, and `hr`. Status is constrained to `scheduled`, `completed`, `cancelled`, and `rescheduled`; result is constrained to `pending`, `passed`, or `failed`. Existing `no_show` values are migrated to `failed` because the requested result vocabulary does not include a no-show value.
