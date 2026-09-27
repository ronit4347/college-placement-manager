# Student management

Student identities use the existing `users` table for name, email, role, and account activation. The `students` table stores the profile fields: phone, roll number, branch, CGPA, graduation year, backlogs, and an opaque resume filename. Skills use the existing `skills` and `student_skills` tables. Student registration creates an empty student profile; academic details remain unset until supplied by the student or an administrator.

## API

All routes require a valid bearer access token except student account registration and login (documented in the main README). Students can access only their own `/me` endpoints. Admin routes require the `ADMIN` role.

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/students/me` | Student | Read own profile and profile completion percentage. |
| `PATCH` | `/api/students/me` | Student | Update own name, email, phone, roll number, branch, CGPA, graduation year, and backlog count. |
| `PUT` | `/api/students/me/skills` | Student | Replace own skill list. |
| `POST` | `/api/students/me/resume` | Student | Upload or replace own PDF resume. |
| `GET` | `/api/students/me/resume` | Student | Download own resume. |
| `GET` | `/api/students` | Admin | List active student accounts (`limit` and `offset` supported). |
| `POST` | `/api/students` | Admin | Create a student account and profile. |
| `GET` | `/api/students/{student_id}` | Admin | Read a student profile. |
| `PATCH` | `/api/students/{student_id}` | Admin | Update a student profile. |
| `PUT` | `/api/students/{student_id}/skills` | Admin | Replace a student's skills. |
| `POST` | `/api/students/{student_id}/resume` | Admin | Upload or replace a student's PDF resume. |
| `GET` | `/api/students/{student_id}/resume` | Admin | Download a student's resume. |
| `DELETE` | `/api/students/{student_id}` | Admin | Deactivate the account while preserving placement history. |

## Validation and privacy

- Email is syntax-validated and normalized to lowercase. The database enforces uniqueness.
- Roll numbers are normalized to uppercase, validated, and unique; a missing roll number is allowed until the profile is completed.
- CGPA must be between 0 and 10, graduation year between 2000 and 2100, and backlogs cannot be negative.
- Skills are trimmed, limited to 50 values, limited to 100 characters each, and duplicate names are rejected case-insensitively.
- Resume uploads accept only `.pdf`/`application/pdf`, check the `%PDF-` signature, and enforce the configured maximum size (5 MiB by default, adjustable up to 25 MiB).
- Resume files use random server-generated names and are stored outside the web root in `RESUME_UPLOAD_DIR`. Downloads require authentication and are scoped to the student or an admin. For production, configure private durable object storage and malware scanning.
- Profile completion counts name, email, phone, roll number, branch, CGPA, graduation year, backlogs, at least one skill, and an uploaded resume.
- Student deletion is a soft deactivation so applications and placement history are retained.

Validation for ownership and roles is enforced by the backend; frontend route guards provide navigation behavior only and are not treated as security boundaries.
