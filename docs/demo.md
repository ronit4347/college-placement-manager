# Local demo dataset

The development seed creates fictional campus placement data through the existing SQLAlchemy models and workflow services. It is repeatable: rerunning it finds the demo records by stable emails/names and does not duplicate or delete them. Demo-owned users are reactivated and their password hashes are synchronized to the currently configured demo passwords. Existing non-demo records are left alone.

## Demo accounts

Set a different strong password (at least 12 characters) for each role in the ignored local `.env` file. Passwords are never stored in the repository, printed by the seed command, or persisted as plaintext.

| Role | Login email | Password environment variable |
| --- | --- | --- |
| ADMIN | `admin@demo.college-placement.example.edu` | `DEMO_ADMIN_PASSWORD` |
| STUDENT | `student01@demo.college-placement.example.edu` | `DEMO_STUDENT_PASSWORD` |
| RECRUITER | `recruiter@demo.college-placement.example.edu` | `DEMO_RECRUITER_PASSWORD` |
| INTERVIEWER | `interviewer@demo.college-placement.example.edu` | `DEMO_INTERVIEWER_PASSWORD` |

All 30 student demo accounts (`student01` through `student30`) use the configured `DEMO_STUDENT_PASSWORD`. The recruiter is attached to Blue Oak Robotics. All demo passwords are hashed with the application's Argon2 password hashing before storage.

Demo ADMIN and INTERVIEWER identities are created only by the seed process. Outside the demo seed, ADMIN creation is restricted to trusted bootstrap administration; interviewers are created and managed by an authenticated admin through `/api/admin/interviewers`. Recruiters are provisioned by an admin from a company detail page and cannot self-register.

Generate distinct local passwords, for example with `openssl rand -base64 24`, and put the results in `.env`. Also set `DEMO_SEED_ENABLED=true`. Keep this enabled only in a local/development environment. The seed command refuses to run unless explicitly enabled and does not erase existing data.

## Run

From the repository root, configure `.env` with `DATABASE_URL`, a random `JWT_SECRET_KEY`, the four demo passwords, and `DEMO_SEED_ENABLED=true`. Then run:

```bash
cd backend
source .venv/bin/activate  # Windows: .venv\Scripts\activate
alembic upgrade head
python -m app.db.seed_demo
```

Run `python -m app.db.seed_demo` again at any time to reconcile the same demo records. This seed creates 30 student profiles, five employers, eight job drives (six published, one draft, one closed), 22 skills, and multiple applications/interviews/offers across applied, shortlisted, interview, rejected, selected, offered, accepted, and joined states. Some students intentionally fail job eligibility criteria so the demo can show both outcomes.

## Demo walkthrough

1. Log in as the student and review the profile, published jobs, eligibility reasons, applications, interview schedule, and offer decision.
2. Log in as the admin to review the student directory, employer/job-drive management, application stages, and database-backed placement analytics.
3. Log in as the recruiter to see the Blue Oak Robotics job drives and company-scoped applications/offers.
4. Log in as the interviewer to see assigned interviews and candidate information allowed by the interviewer workflow.

The backend test `backend/tests/test_demo_seed.py` verifies repeatability and exercises these data through login and dashboard, job, eligibility, application, interview, offer, recruiter, and interviewer APIs against an isolated SQLite database. Use PostgreSQL migrations for a normal local application run.
