# College Placement Manager

## Problem statement

College placement activity spans students, eligibility checks, job drives, applications, interviews, offers, and reporting. Coordinating this lifecycle across disconnected tools makes it difficult to keep information consistent and understand placement progress.

## Proposed solution

College Placement Manager is planned as a role-aware application for coordinating the placement lifecycle from student eligibility through placement analytics. This foundation establishes the frontend, API service, configuration, and documentation. Business workflows are future milestones.

## Technology stack

- Frontend: React, Vite, TypeScript, Tailwind CSS, React Router, Axios, Recharts
- Backend: Python, FastAPI, SQLAlchemy, Pydantic, Alembic
- Database: PostgreSQL with SQLAlchemy models and Alembic migrations
- Development: Git, environment variables, Docker-ready project structure

## Current implementation status
The student dashboard includes a resume analyzer for published jobs. Mock mode works without an API key; Gemini mode uses a server-side `AI_API_KEY`. The key must never be committed to GitHub. AI analysis is decision support for students, not an automated hiring decision, and personal identifiers are minimized before external analysis. See [docs/ai.md](docs/ai.md) for configuration, privacy boundaries, and failure behavior.


- Responsive React application shell and home page
- Frontend backend-health status check at `/api/health`
- FastAPI health endpoint
- PostgreSQL schema for the core placement entities, with migration and development skill seed
- Environment-based database and future secret configuration in `.env.example`
- Password-hashed student registration, JWT login, current-user endpoint, and role authorization
- Student, admin, recruiter, and interviewer role-protected frontend routes
- Student profile CRUD, skills, profile completion, and validated PDF resume management
- Student resume-to-job analysis with deterministic mock mode and an optional backend-only Gemini provider
- User-scoped in-app notifications for application, interview, selection, and offer events
- Backend-driven search, filtering, and pagination for admin and student placement lists
- Admin-only company management, employer search and filtering, company activation, and recruiter company assignment
- Admin job drive creation and lifecycle management, student published-drive search, recruiter company-scoped listings, and admin applicant viewing
- Reusable student placement eligibility evaluation with a student-only API endpoint and detailed reasons
- Eligibility-gated application submission, duplicate/deadline protections, role-scoped application access, status transitions, offers, and status history
- Interview scheduling and interviewer results with student privacy scopes
- Admin selection and offer creation/issue, student accept/decline, and recruiter company-scoped offer views
- Admin placement dashboard with database-backed KPIs and Recharts analytics

## Prerequisites

- Node.js and npm
- Python 3.10 or newer
- PostgreSQL 14 or newer for local application data
- Docker Engine and Docker Compose v2 (recommended for the full local stack)

## Run with Docker Compose

The Compose stack starts PostgreSQL, applies Alembic migrations before launching the FastAPI development server, and starts Vite with hot reload. The frontend proxies `/api` requests to the backend container.

1. Copy `.env.example` to `.env` in the repository root.
2. Set a fresh JWT key in `.env` (generate it with `openssl rand -hex 32`). The example PostgreSQL password is for local development only; replace it if desired. Keep database passwords URL-safe (for example, letters, numbers, and hyphens) because Compose builds the backend connection URL from these values.
3. Start the stack:

```bash
docker compose up --build
```

Open the frontend at `http://localhost:5173`, the API at `http://localhost:8000`, and the PostgreSQL service on port `5432`. PostgreSQL data and uploaded resumes use named Docker volumes. Source folders are bind-mounted for development reloads. Later starts can use `docker compose up`.

Compose runs `alembic upgrade head` whenever the backend container starts. To apply migrations manually:

```bash
docker compose run --rm backend alembic upgrade head
```

To seed the common skill catalog:

```bash
docker compose exec backend python -m app.db.seed
```

To seed the full fictional demo, set `DEMO_SEED_ENABLED=true` and the four `DEMO_*_PASSWORD` values in `.env` before starting the containers, then run:

```bash
docker compose exec backend python -m app.db.seed_demo
```

See [docs/demo.md](docs/demo.md) for demo login identities and walkthrough. Do not use development credentials or this Compose configuration for production deployment.

To stop containers while keeping database/resume data, press Ctrl+C or run `docker compose down`.

## Environment setup

Copy `.env.example` to `.env` at the repository root and adjust values for your environment. Generate a random `JWT_SECRET_KEY` with `openssl rand -hex 32` before enabling authentication. `DATABASE_URL` must point to an initialized PostgreSQL database to use registration/login. The frontend uses `VITE_API_URL` for an API origin; when unset, it uses the Vite development proxy.

After configuring PostgreSQL and `DATABASE_URL`, create/update the schema from `backend/` with `alembic upgrade head`. Seed common development skills with `python -m app.db.seed`. For a complete fictional demo dataset and role logins, configure the `DEMO_*` variables in `.env`, enable `DEMO_SEED_ENABLED=true`, and run `python -m app.db.seed_demo` from `backend/`. See [docs/demo.md](docs/demo.md) for the credentials and demo walkthrough, and [docs/database.md](docs/database.md) for the schema and constraints.

## Install and run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (usually `http://localhost:5173`).

## Install and run the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`. The frontend development server proxies `/api` requests to this address. To use another API origin, set `VITE_API_URL` in `frontend/.env.local`.

Public registration accepts only email, name, and password and always creates a `STUDENT`; privileged role fields are rejected by the API. Admin accounts are controlled through trusted bootstrap administration (the development demo admin is created only by the guarded seed process). An `ADMIN` can create, list, activate, and suspend interviewers through `/api/admin/interviewers`. Recruiter accounts cannot be self-registered: an `ADMIN` provisions them through the company recruiter workflow, attached to an active company, before recruiter access is granted. Backend role and ownership checks are enforced independently of frontend route guards. See [docs/authorization.md](docs/authorization.md) for the role model and endpoints.

## Authentication API

- `POST /api/auth/register` — validate input and create a student account using an Argon2 password hash.
- `POST /api/auth/login` — verify credentials and issue a short-lived HS256 JWT access token.
- `GET /api/auth/me` — return the active authenticated user's public profile; send the token as `Authorization: Bearer <token>`.

Backend tests: `cd backend && .venv/bin/pytest -q`.

Student profile and administration endpoints are listed in [docs/student-management.md](docs/student-management.md). Apply the student-profile database migration with `cd backend && .venv/bin/alembic upgrade head` after setting `DATABASE_URL`.

Company administration endpoints, recruiter assignment rules, and company data behavior are documented in [docs/company-management.md](docs/company-management.md). Apply all database migrations with `cd backend && .venv/bin/alembic upgrade head`.

Job drive fields, role visibility, lifecycle transitions, endpoints, and their validation are documented in [docs/job-drives.md](docs/job-drives.md).

Eligibility criteria, missing-data behavior, API access rules, and frontend feedback are documented in [docs/eligibility.md](docs/eligibility.md).

Application submission rules, the status transition graph, visibility scopes, and endpoints are documented in [docs/applications.md](docs/applications.md).

Interview rounds, role scopes, status/result rules, and endpoints are documented in [docs/interviews.md](docs/interviews.md).

Selection requirements, offer lifecycle, access scopes, and endpoints are documented in [docs/offers.md](docs/offers.md).

Admin dashboard KPI definitions, filters, and analytics endpoints are documented in [docs/analytics.md](docs/analytics.md).

Run backend tests with `cd backend && .venv/bin/pytest -q` and create a frontend production build with `cd frontend && npm run build`.

## Production deployment

Render's separate static frontend, FastAPI web service, and managed PostgreSQL configuration is documented in [docs/deployment-render.md](docs/deployment-render.md) and defined in [`render.yaml`](render.yaml). It includes explicit Alembic pre-deploy migrations and persistent resume storage requirements. Deployment must still be completed and verified in your Render account.

## Current API endpoint

- `GET /api/health` — returns `{"status":"ok"}` when the API is running.

## Future milestones

1. Extended placement reports and exports

See [docs/requirements.md](docs/requirements.md) for the initial requirements.
