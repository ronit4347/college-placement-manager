# Test pass results

**Run date:** 2026-09-25

## Results

| Check | Command | Result |
| --- | --- | --- |
| Backend suite | `cd backend && ./.venv/bin/python -m pytest -q` | **65 passed**, 1 Starlette/httpx deprecation warning, 11.73 seconds |
| Backend syntax/import compilation | `cd backend && ./.venv/bin/python -m compileall -q app tests` | Passed |
| Frontend TypeScript and production build | `cd frontend && npm run build` | Passed (`tsc -b` and Vite production build) |

## Role provisioning security retest

- Public registration without a role creates a STUDENT account; requests trying to assign ADMIN, INTERVIEWER, or RECRUITER are rejected with 422 and create no account.
- Student profile updates cannot assign a role. A student cannot access admin endpoints.
- ADMIN, RECRUITER, and INTERVIEWER are each denied admin-only endpoints; authorized ADMIN actions still work.
- Admin-created interviewers receive only interviewer access, duplicate emails return 409, and deactivated interviewer credentials cannot log in.
- Existing company tests continue to cover ADMIN-only recruiter provisioning and recruiter company scoping.
- The focused auth/company run passed **17 tests**. The complete backend run passed **65 tests**; backend compilation and frontend production build passed.
- No separate frontend unit-test command is defined in the frontend package; validation for this change includes the TypeScript/Vite production build.

The first `pytest -q` attempt used the system Python, which does not have this project's dependencies installed and stopped during collection (`ModuleNotFoundError: jwt`). Re-running with the existing `backend/.venv` completed successfully; this was an interpreter selection issue, not a failing project test.

## Requested workflow coverage

The passing suite covers the requested workflows through route-level tests using FastAPI's test client and an isolated in-memory SQLite database:

- **Auth:** registration, password hashing, duplicate registration, refusal of privileged self-assigned roles, login/current-user, invalid password, invalid token, and role authorization.
- **Student:** own profile edit and cross-user isolation, profile validation and unique roll number, skills replacement/duplicates, resume PDF upload/download, invalid type/signature/size, and admin student management.
- **Company:** admin create/list/detail/update/deactivate, search/filter, validation/duplicate/not-found, recruiter-company association, and unauthorized access.
- **Job drive:** create/edit, draft/published/closed/cancelled lifecycle, invalid transitions, published student visibility, recruiter company scope, and applicants access.
- **Eligibility:** CGPA, backlogs, branch, graduation year, required skills, empty/unconfigured requirements, missing student fields, case-insensitive matching, and multiple simultaneous failures.
- **Application:** eligibility/published/deadline checks, successful apply, duplicate prevention, student ownership, admin/recruiter scoping, valid and invalid status transitions, and timeline.
- **Interview:** scheduling, interviewer assignment/visibility, rescheduling, cancellation, completion/result/feedback, invalid round/time, schedule conflict, and unauthorized access.
- **Offer:** selected-candidate requirement, duplicate active offer, issue, accept, decline, expiry, ownership, recruiter company scope, and invalid transitions.
- **AI:** mock structured analysis, invalid PDF extraction, missing provider key/mock behavior, provider failure, malformed provider result, PII reduction, endpoint authorization, and safe failure responses.
- **RBAC/IDOR:** role-specific checks span admin-only company/job/application/analytics operations; student-only profile, submission, and AI routes; a role matrix that verifies each nonmatching role is denied; student ownership of profiles, applications, resumes, and offers; recruiter company boundaries; interviewer assignment boundaries; and notification ownership.
- **Security middleware:** CORS policy, resume request-body limits, local resume permissions, and no accepted JWT secret in the example configuration.

## Limits of this test pass

- API tests use SQLite in-memory databases for isolation. They do not validate PostgreSQL-specific behavior, production migrations, TLS, or deployment configuration.
- The role matrix covers student-only, admin-only, and interviewer-only operations across all four roles. It is not an exhaustive combinatorial matrix of every role against every individual endpoint.
- AI provider behavior is tested with mocks; this run does not call an external provider or validate its availability/data handling.
- One dependency warning remains: Starlette reports that its current TestClient/httpx integration is deprecated and suggests `httpx2`. Tests pass, but dependency compatibility should be reviewed during an intentional dependency upgrade.
- Passing tests show that covered expectations hold; they do not prove the application is defect-free.
