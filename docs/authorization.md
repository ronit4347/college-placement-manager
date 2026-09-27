# Registration and role authorization

## Public registration

`POST /api/auth/register` accepts only email, full name, and password. The registration schema rejects extra fields, so requests containing a `role` value (including `ADMIN`, `RECRUITER`, `INTERVIEWER`, or even a client-supplied `STUDENT`) receive HTTP 422. The backend assigns `student` explicitly and creates the associated student profile. The frontend registration page is titled **Create Student Account** and has no role selector.

## Controlled accounts

- **ADMIN:** There is no public admin registration endpoint. Admin accounts are provisioned through trusted database/bootstrap administration. The development/demo admin is created by `app.db.seed_demo` only when the local `DEMO_SEED_ENABLED` guard and configured demo credentials are present.
- **INTERVIEWER:** Only an authenticated ADMIN can list, create, activate, or suspend interviewer accounts through `/api/admin/interviewers`. Account creation always assigns the interviewer role in backend code. Deactivation invalidates existing access tokens on their next request because active status is checked from the database.
- **RECRUITER:** There is no public recruiter registration or self-approval flow. The existing `POST /api/companies/{company_id}/recruiters` workflow is ADMIN-only, requires an active company, and creates the user already associated with that company. This administrator-controlled provisioning is the approval boundary: recruiter access begins only after the admin provisions the account. No pending recruiter account has recruiter access.

## Authorization enforcement

The UI hides routes according to the authenticated role for navigation and user experience. It is not the security boundary. Backend route dependencies load the user from the signed token subject and current database row, verify the account remains active, and apply role checks independently. Recruiter data is constrained to the associated company; students are constrained to their own profile/applications/offers/resume; interviewers are constrained to assigned interviews. Profile-update schemas reject unknown `role` or `password_hash` properties, and public account responses never include password hashes.

Login accepts only email and password. After login, the frontend retrieves `/api/auth/me`; the database-backed role routes the user to `/student`, `/admin`, `/recruiter`, or `/interviewer`. The login form has no role selection.

## Status codes

- 401: missing/invalid credentials or an inactive account's token.
- 403: authenticated user lacks the role or resource permission.
- 409: duplicate account or conflicting provisioning operation.
- 422: invalid registration/profile/provisioning fields, including an attempted public role field.
