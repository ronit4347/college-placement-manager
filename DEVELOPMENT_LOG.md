# Development Log

## Foundation milestone

- Created the React, Vite, TypeScript, Tailwind CSS, and React Router frontend shell.
- Added an Axios health-check service and a backend status panel on the home page.
- Created the FastAPI application and `GET /api/health` endpoint.
- Added backend package structure, dependency declarations, and environment placeholders.
- Added project requirements, setup instructions, and ignore rules.

## PostgreSQL database architecture

- Added SQLAlchemy models for users, students, companies, job drives, applications, interviews, offers, skills, and the student/job skill associations.
- Added timestamps, foreign keys, delete policies, unique and check constraints, and query indexes.
- Added environment-driven engine/session setup and Alembic configuration with the initial schema migration.
- Added an idempotent development seed command for a small set of skill names; it does not create sample users or credentials.
- Documented entity semantics, relationships, constraints, and service-layer business rules in `docs/database.md`.
- Applied the migration to local PostgreSQL 16 and verified the complete table set; also verified migration compatibility against a temporary SQLite database.

## Authentication and authorization

- Added student-only public registration, Argon2 password hashing, JWT login, and authenticated current-user retrieval.
- Added request-scoped database sessions, bearer-token validation, active-user checks, and reusable role authorization dependencies.
- Added login and registration screens, auth context, session-scoped token handling, logout, protected routes, role-specific routes, and an unauthorized page.
- Added backend tests for registration, duplicate registration, login, incorrect password, invalid token, and role authorization.
- Configured JWT secret and token lifetime through environment variables; no secret is embedded in application code.
- Verification passed: seven backend auth tests and the frontend production build.

## Student management

- Extended student profiles with phone and nullable academic fields so new student accounts can start incomplete; added an Alembic migration.
- Added student self-service profile endpoints, skills replacement, own-resume upload/download, and admin student CRUD/skills/resume operations.
- Added profile validation, unique roll number handling, role/ownership checks, profile completion calculation, and soft deactivation to preserve placement history.
- Added private local PDF storage with MIME, signature, and configurable size validation; new uploads replace prior files after the database update succeeds.
- Added the student dashboard for profile editing, skills, resume management, and completion progress.
- Added student-management API and validation documentation.
- Verification passed: 12 backend tests, backend bytecode compilation, PostgreSQL migration/drift check, and frontend production build.
- Added a database foundation note documenting the environment-based PostgreSQL configuration.
- Aligned the health response with the requested `{"status":"ok"}` contract.

## Company management

- Extended the company schema with location and HR contact details; added a recruiter-to-company foreign key and a database check constraint requiring that association for recruiter accounts.
- Added an Alembic migration for company fields, indexes, recruiter association, and the recruiter association constraint.
- Added admin-only company search, filtering, create, detail, edit, activate/deactivate, recruiter provisioning, and recruiter reassignment APIs.
- Added the admin company list, search/filter controls, company details, create/edit forms, status controls, and recruiter provisioning form.
- Added tests for company validation and duplicate handling, role authorization, search/filtering, status changes, recruiter association and reassignment, and the database association constraint.
- Added company API and relationship documentation.
- Verification passed: 16 backend tests, backend bytecode compilation, frontend production build, API health check, PostgreSQL migration to `c042a2b34e40`, and `alembic check` with no schema drift.

## Job drive management

- Added schemas and validation for employer, role details, INR LPA package ranges, eligibility, required skills, deadline, and employment type.
- Added admin create/edit and explicit publish, close, and cancel lifecycle endpoints; invalid transitions and publishing without a future timezone-aware deadline are rejected.
- Added published-drive search/details for students, company-scoped drive search/details for recruiters, and admin search/filter plus read-only applicant listing.
- Added database checks and a company/status index to support valid compensation and graduation criteria and common company drive queries.
- Added admin job drive forms/details/status controls/applicant list and student/recruiter role-specific search/detail pages.
- Added tests for lifecycle, validation, visibility scoping, inactive company behavior, authorization, and applicant viewing.
- Added [docs/job-drives.md](docs/job-drives.md). Application submission remains outside this milestone.
- Verification passed: 20 backend tests, backend bytecode compilation, API health check, frontend production build, PostgreSQL migration to `868f83a9e574`, and `alembic check` with no schema drift.

## Placement eligibility engine

- Added a standalone service that evaluates CGPA, backlog limit, allowed branches, graduation year, and required skills and returns structured eligibility plus all reasons.
- Missing configured student data fails closed with field-specific reasons; missing criteria impose no restriction; empty skill requirements do not require student skills.
- Added `GET /api/job-drives/{job_drive_id}/eligibility`, restricted to the authenticated student's own profile and published drives. It uses persisted profile/drive data and accepts no student-supplied criteria values.
- Added the eligibility result panel and reasons to student job drive details.
- Added unit coverage for passing boundaries, case-insensitive matching, missing profiles/data, no/empty criteria, individual omitted requirements, and multiple simultaneous failures, plus endpoint authorization and persisted-profile behavior.
- Documented the evaluation rules and intended server-side reuse before future application submission in `docs/eligibility.md`.
- Verification passed: all 33 backend tests, backend bytecode compilation, frontend production build, API health smoke check, and OpenAPI registration check for the eligibility endpoint.

## Job application workflow

- Added eligibility-checked student application submission with published-drive, deadline, duplicate, and saved-profile checks performed server-side.
- Added student-owned, admin-wide, and recruiter-company-scoped application list/detail APIs; status mutation is admin-only.
- Added a service-enforced status graph for applied, shortlisted, rejected, interview, selected, offered, and joined stages.
- Added status-history events with actor, note, and timestamp. Moving an application to offered creates a pending offer; joining marks the offer accepted.
- Added an Alembic migration replacing the application status constraint, mapping legacy statuses, adding/backfilling status history, and retaining the existing duplicate constraint.
- Added student Apply/confirmation and My Applications, application details/timeline, admin status management, and recruiter-scoped application screens.
- Added tests for eligibility, publication/deadline gates, duplicate applications, role/scope access, invalid and valid transitions, history, and offer state.
- Documented business rules and endpoints in `docs/applications.md`.
- Verification passed: 38 backend tests, backend bytecode compilation, frontend production build, API health/OpenAPI checks, PostgreSQL migration to `3c7a1b9e5d21`, and `alembic check` with no schema drift.

## Interview management

- Extended interviews with constrained Aptitude, Technical, Managerial, and HR rounds and the requested scheduled, rescheduled, completed, and cancelled states; result values are pending, passed, or failed.
- Added admin scheduling, interviewer assignment, rescheduling, and cancellation. Scheduling validates shortlisted application state, future timezone-aware dates, active interviewer accounts, allowed duration, and interviewer overlap.
- Added interviewer-only assigned interview views and result/feedback submission. Students can only access their own schedules, and their response excludes interviewer feedback and candidate detail fields.
- Added admin, interviewer, and student interview pages with scheduling, assignment, reschedule/cancel actions, and result entry; linked them from each role workspace/dashboard.
- Added PostgreSQL migration for round/status/result constraints. Existing `no_show` result values migrate to `failed` to fit the requested result set.
- Added API tests for role scoping, field validation, interviewer assignment, passing/failing results, rescheduling, cancellation, and overlapping schedule rejection. See `docs/interviews.md`.
- Verification: 40 backend tests passed; frontend TypeScript production build passed.

## Selection and offer management

- Kept candidate selection behind the ADMIN-only application status endpoint and removed direct status updates to OFFERED; issuing an offer now advances a selected application to OFFERED and records the timeline event.
- Added DRAFT, ISSUED, ACCEPTED, DECLINED, and EXPIRED offer lifecycle with salary/currency, joining date, optional expiry, and offer letter reference.
- Added admin draft creation, issue and expire actions; student-owned offer views and accept/decline; recruiter views scoped to their company.
- Added a database partial unique index allowing only one active draft/issued offer per application while preserving terminal offer history.
- Added offer management UI for admins, students, and recruiters and documented access/business rules in `docs/offers.md`.
- Added tests for non-selected candidates, duplicate active offers, accept, decline, automatic expiry, student ownership, recruiter company scope, and the application selection-to-join flow.
- Verification passed: all 42 backend tests, frontend production build, PostgreSQL migration to `ab61c94df823`, and `alembic check` with no schema drift.

## Admin analytics dashboard

- Replaced the admin placeholder with a database-backed dashboard for student, employer, drive, application, shortlist, interview, selection, offer, and placement metrics.
- Added an ADMIN-only analytics service/API and database-driven filter options for graduation year, branch, company, and application submission date range.
- Added Recharts visualizations for placement by branch, application funnel, company selections, INR offer package distribution, and monthly placements.
- Defined placement rate as joined students divided by the selected registered student cohort and documented metric definitions in `docs/analytics.md`.
- Added loading skeletons, chart empty states, retryable errors, filter apply/reset, and admin navigation shortcuts. The chart dashboard is lazy-loaded.
- Added API tests using persisted student, company, job drive, application, interview, offer, and status history data; covered filters, empty cohorts, and role authorization.
- Verification passed: 43 backend tests, Python bytecode compilation, frontend production build, and read-only analytics/filter queries against PostgreSQL.

## Student placement dashboard

- Expanded the student dashboard with CGPA, branch, skills, profile completion, applied-job count, selection state, upcoming interviews, and current offer summaries using the student's persisted records.
- Added per-application placement timelines combining application history, scheduled interview rounds, and offer decisions.
- Added student-specific eligible-job search and filters for keywords, location, employment type, and graduation year; the backend evaluates the saved profile through the shared eligibility engine in one scoped endpoint.
- Student offer lists and detail views now omit draft offers until administration issues them.
- Verification: backend Python compilation and frontend TypeScript/production build passed.

## AI resume analyzer

- Added backend PDF text extraction for the student's existing validated resume upload, with encrypted/invalid PDF handling, page and character bounds, and direct-identifier minimization before any external provider call.
- Added a `ResumeAnalyzer` abstraction with deterministic offline mock mode and an optional backend-only OpenAI provider using strict structured JSON output and Pydantic validation.
- Added the student-only `POST /api/students/me/resume-analysis` endpoint. It loads only the student's own resume and a published persisted job drive; analysis does not write application or selection state.
- Added the student dashboard analyzer with job selection, loading/error states, estimated match score, matching/missing skills, education and experience evidence, suggestions, and explicit decision-support labeling.
- Added analyzer tests covering mock output, identifier removal, unreadable PDF, provider network failure, malformed AI output, endpoint success, and missing resume.
- Documented the backend prompt, data handling, response, configuration, limitations, and decision boundary in [docs/ai.md](docs/ai.md).
- Verification passed: all 51 backend tests, backend bytecode compilation, and frontend TypeScript/Vite production build. The full suite also exposed an existing offer-scope test that expected an unissued draft to be visible to students; corrected the test to check privacy before issue and ownership after issue, matching the implemented workflow.

## In-app notifications

- Added the user-owned notifications table with a cascading user foreign key, supported event-type constraint, timestamp/read state, and unread-list index; added the Alembic migration `cc27a30491b2`.
- Generated notifications transactionally for application submitted/shortlisted/rejected, interview scheduled/rescheduled/result, candidate selected, and offer issued. New applications notify the student, active admins, and recruiters at the relevant company; interview scheduling also notifies the assigned interviewer.
- Added authenticated list, unread-count, and mark-read endpoints. Cross-account notification IDs return 404.
- Added the header notification dropdown with polling unread badge, read/unread styling, relative times, navigation, loading, and error states.
- Documented recipients and API behavior in [docs/notifications.md](docs/notifications.md).

## Search and filtering

- Expanded admin student search to name/email, roll number, branch, CGPA range, and application-derived placement status; added an admin student directory page with paging.
- Added company name/industry filters and job drive company/status/location/package filters. Application lists now filter by company, job title, workflow status, and student branch.
- Added student job filters for company, location, package range, persisted eligibility, and the current student's application status. Eligibility and status are read from backend profile/workflow data.
- Added bounded limit/offset controls across list pages. Frontend page changes are reset when filters change, and a one-row lookahead keeps next/previous controls accurate.
- Documented filter semantics in [docs/search-filtering.md](docs/search-filtering.md).
# Security audit

- Reviewed authentication, authorization/ownership checks, JWT handling, password hashing, validation and database query patterns, CORS, environment-backed secrets, AI provider handling, error responses, and resume upload/storage paths.
- Fixed validation response reflection, genericized an authentication configuration error, removed the usable JWT secret from `.env.example`, narrowed CORS, restricted resume filesystem permissions, and capped resume request bodies before multipart parsing.
- Added regression coverage for those changes in auth, student, and security tests.
- Added `docs/security.md` with the audit scope, findings, verification, and remaining deployment risks.
- Verification: backend suite passed (59 tests); Python application modules compile successfully.
- Remaining concerns include shared rate limiting, sessionStorage token exposure in the presence of XSS, heuristic AI PII reduction, and deployment-level TLS/secret/dependency controls; details are in `docs/security.md`.

# Full test pass

- Ran the backend suite with the project's `backend/.venv`: 60 passed, with one Starlette/httpx deprecation warning.
- The initial system-Python invocation could not collect tests because PyJWT is installed only in the project environment; rerunning with the project interpreter passed.
- Ran backend `compileall` and the frontend TypeScript/Vite production build successfully.
- Added `docs/testing.md` with feature coverage, commands/results, and test environment limitations. Backend route tests use in-memory SQLite; they do not replace PostgreSQL/deployment verification.
- Added a role matrix regression test that checks all four roles against student-only, admin-only, and interviewer-only operations.

# UI design pass

- Reviewed the shared app shell and the login, student dashboard/profile, job drives, applications, interviews, offers, admin analytics dashboard, students, companies, job-drive detail/form/applicant, company detail/form, AI resume analysis, and notification UI.
- Added role-aware sidebar navigation, a more structured top bar/account area, compact responsive navigation, and a skip link with visible keyboard focus.
- Consolidated the global color tokens, buttons, form controls, table typography, panel shadows, focus states, and reduced-motion behavior in `frontend/src/styles.css` and Tailwind configuration.
- Improved notification panel Escape-key dismissal and accessible control linkage; aligned dashboard chart colors with the application brand palette.
- Existing pages retain their routes, API calls, filters, forms, and role behavior. The current UI has no dialog/modal workflow; shared dialog styling is available without introducing a new interaction.
- Verification: `cd frontend && npm run build` passed (TypeScript and Vite production build).

# Fictional demo seed

- Added an explicitly enabled, repeatable demo seed command at `backend/app/db/seed_demo.py`; it upserts records through the existing SQLAlchemy models and workflow services and does not delete existing data.
- Added 30 fictional student accounts/profiles, five employers, eight job drives, 22 skills, 33 eligible applications, 24 interviews, and eight offers in the isolated CLI run. Workflow stages include applications, shortlisting, interviews/results, rejection, selection, issued/accepted offers, and joined placements.
- Added four role demo login emails. Passwords are provided by local-only `DEMO_*_PASSWORD` environment variables, Argon2-hashed, omitted from command output, and never checked into source. `DEMO_SEED_ENABLED=true` is required to run the command.
- Documented setup and login identities in `docs/demo.md`, added `.env.example` placeholders, and linked the guide from README.
- Verified the command twice against a temporary SQLite database (second run added zero duplicate applications) and exercised seeded login, student profile/jobs/eligibility/applications/interviews/offers, recruiter job scoping, interviewer schedule, and admin analytics APIs.
- Final backend verification: `cd backend && ./.venv/bin/python -m pytest -q` passed (61 tests, one existing Starlette/httpx deprecation warning); `compileall` passed. The demo smoke database was temporary SQLite; normal local runs should use PostgreSQL migrations.

# Docker Compose development environment

- Added Python 3.12 backend and Node 22 frontend development Dockerfiles, scoped Docker build ignores, and a Compose stack with PostgreSQL 16, database health checks, persistent database/resume volumes, backend startup migrations, FastAPI health checks, and Vite-to-backend proxying.
- Updated Vite's proxy target to use the `VITE_API_PROXY_TARGET` environment variable while retaining localhost behavior for non-container development.
- Added PostgreSQL/Compose environment placeholders and documented Docker startup, migration, skill seed, and demo seed procedures in README.
- Validation: `docker compose config --quiet` passed with the example environment and a temporary JWT value; Alembic migration history loaded; frontend build passed.
- Full Docker image/container startup could not be completed: the Docker CLI is installed, but the Docker daemon is not running/available in this environment (socket connection refused; the discovered Docker.app bundle has no executable). No container startup result is claimed.

# Registration and role-assignment security

- Confirmed public registration accepts only name, email, and password and sets STUDENT on the server. Attempts to send ADMIN, INTERVIEWER, or RECRUITER are rejected; student profile updates reject role fields.
- Added ADMIN-only interviewer management endpoints and UI. Interviewers are created with a fixed role, passwords are hashed, responses omit credential fields, and admins can deactivate/reactivate accounts. Deactivated accounts are denied by the existing active-account authentication check.
- Preserved the existing recruiter approval boundary: only an ADMIN can provision a recruiter and associate them with an active company. There is no public recruiter-registration route.
- Kept login role-neutral; `/workspace` now routes authenticated users to the dashboard for their database-backed role. Registration is labeled “Create Student Account.”
- Added role-provisioning documentation in `docs/authorization.md` and updated README, security, demo, and testing documentation.
- Verification: focused auth/company tests passed (17); full backend suite passed (65, one existing Starlette/httpx deprecation warning); backend `compileall` passed; frontend TypeScript/Vite production build passed.

# Career platform frontend redesign

- Reworked the public home page into a responsive career-platform landing experience with original Campus identity, search, live API status, opportunity discovery, company discovery based only on published drives visible to the signed-in role, career categories, AI decision-support explanation, placement journey, recruiter/student/college sections, and a product-style footer. Anonymous users see no invented placement metrics or fabricated job/company records.
- Added a reusable opportunity card and applied it to live landing and job-search results. The landing search carries its query through login to the existing role-protected listing route.
- Updated public/mobile navigation, role workspace styling, sign-in/registration presentation, student dashboard greeting/profile completion, student application progress cards, job detail layout with sticky eligibility/apply panel, and role-specific recruiter/interviewer dashboards populated through existing scoped APIs. Admin analytics, interviews, offers, notifications, and management workflows retain their API services and actions.
- Improved interview form accessible names and responsive layouts; kept all role checks, eligibility, application, interview, offer, and AI decisions in their existing backend services.
- Verification: frontend TypeScript/Vite production build passed; full backend suite passed (65 tests) and Python compilation passed. A local Vite dev server could not bind in this sandbox (`listen EPERM`), so an interactive browser/screenshot review was unavailable. Frontend package has no separate UI test runner.
