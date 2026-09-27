# Search, filters, and pagination

List filters are applied in backend queries, and list endpoints use bounded `limit`/`offset` pagination. The frontend requests 21 records and displays 20 to tell whether a next page exists without showing an empty page at exact page boundaries. Changing any filter resets the page to the first page.

## Admin filters

- `GET /api/students`: name/email (`q`), roll number, branch, CGPA min/max, and placement status. Placement status is the highest current workflow state across the student's applications (`JOINED` is shown as `PLACED`); `NOT_APPLIED` matches students with no applications.
- `GET /api/companies`: company `name`, `industry`, and active state.
- `GET /api/job-drives`: company name, title/description/company search, status, location, package range, employment type, and graduation year.
- `GET /api/applications`: company name, job title, status, and student branch.

## Student filters

- `GET /api/job-drives`: company name, location, package range, eligibility (`eligibility=true|false`), and application status (`NOT_APPLIED` or a workflow status). Eligibility is evaluated from the authenticated student's saved profile and persisted job requirements. Application status is scoped to that student's applications.

Student-only filters are ignored or rejected for other roles as appropriate. Job and application responses include the student's current eligibility/application status for display. All filters compose with `limit` and `offset`.
