# In-app notifications

Notifications are persisted, user-owned records. The event and notification are written in the same database transaction so a failed workflow update cannot leave a misleading notification.

## Events and recipients

| Event | Recipients |
| --- | --- |
| Application submitted | Student, active placement admins, and active recruiters assigned to that drive's company |
| Application shortlisted or rejected | Student |
| Interview scheduled or rescheduled | Student and currently assigned interviewer |
| Interview result | Student |
| Candidate selected | Student |
| Offer issued | Student |

No email or SMS delivery is configured. Notifications are retained until normal account deletion; read notifications remain available in the list.

## API

All endpoints require a bearer token and query only records whose `user_id` matches that token's active account.

- `GET /api/notifications?limit=30&offset=0` returns the current user's newest notifications.
- `GET /api/notifications/unread-count` returns `{ "unread_count": 0 }`.
- `PATCH /api/notifications/{notification_id}/read` marks one of the current user's notifications read. It is idempotent; IDs belonging to another user return 404.

The notification dropdown refreshes the unread badge every 30 seconds and loads the latest notifications when opened. Opening an unread item marks it as read and navigates to its related placement page.
