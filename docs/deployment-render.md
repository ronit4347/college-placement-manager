# Render production deployment

This repository is prepared for three separate Render services:

```text
Browser → Render Static Site (React/Vite) → HTTPS → Render Web Service (FastAPI) → Render PostgreSQL
```

The checked-in [`render.yaml`](../render.yaml) defines the services, runs Alembic before each API deploy, uses Render's health check, and puts uploaded resumes on a backend persistent disk. It contains no credentials.

## Before deploying

1. Commit and push this repository to a Git provider Render can access. This working copy has no `.git` directory, so Git history and whether any past commit exposed credentials could not be audited here.
2. Ensure the Render service names in `render.yaml` are available. The expected default origins are:
   - Frontend: `https://college-placement-manager-ronith.onrender.com`
   - API: `https://college-placement-manager-ronith-api.onrender.com`
3. If Render requires different names or you use custom domains, set the backend `FRONTEND_URL` to the exact frontend origin (scheme + hostname, no path or trailing slash), and set the static site's `VITE_API_URL` to the API origin (scheme + hostname, no `/api` suffix). Redeploy both services after changing these values.

## Create the Render services

1. In Render, choose **New → Blueprint**, connect the pushed repository, and select its root `render.yaml`.
2. Review the proposed resources before applying:
   - PostgreSQL: `college-placement-manager-db`, Singapore region, `0.5c-1g` plan, internal-only network access.
   - API: `college-placement-manager-ronith-api`, Python native runtime, root `backend`, Singapore region, `0.5c-512mb` plan, one 1 GB persistent disk at `/opt/render/project/src/uploads/resumes`.
   - Frontend: `college-placement-manager-ronith`, static site, root `frontend`, built from `npm ci && npm run build`, published from `dist`, with SPA route rewrites.
3. If prompted for `AI_API_KEY`, leave it blank to use the existing mock analyzer, or enter the provider key in the Render dashboard. Never set it on the static site or in a `VITE_` variable.
4. Apply the Blueprint. The API's pre-deploy command runs `alembic upgrade head`; the API starts with Uvicorn bound to `0.0.0.0:$PORT`. Wait for the `/api/health` health check to pass.
5. Confirm the actual Render URLs. If they differ from the expected defaults or you set custom domains, update API `FRONTEND_URL` and static-site `VITE_API_URL` as described above. Redeploy, then check that `GET https://<api-host>/api/health` returns `{"status":"ok"}` and the browser can call the API without a CORS error.
6. Register an initial student through the public frontend. Provision the first administrator through the existing trusted administrative process; public registration always creates a student. Do not enable demo seeding in production.

## Environment variables

Render supplies `DATABASE_URL` from its private PostgreSQL connection string and generates `JWT_SECRET_KEY`. The backend also uses:

| Variable | Production value |
| --- | --- |
| `DATABASE_URL` | Render PostgreSQL internal connection string; normalized to the installed `psycopg` 3 SQLAlchemy driver |
| `JWT_SECRET_KEY` | Generated 256-bit secret; rotate only through a planned token invalidation |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` |
| `FRONTEND_URL` | Exact HTTPS static-site origin; restricts backend CORS |
| `AI_API_KEY` | Optional backend-only provider key; blank selects the existing mock mode |
| `AI_MODEL` | `gpt-4o-mini` unless you intentionally choose another supported model |
| `AI_REQUEST_TIMEOUT_SECONDS` | `25` |
| `AI_MAX_RESUME_CHARACTERS` | `30000` |
| `RESUME_UPLOAD_DIR` | `/opt/render/project/src/uploads/resumes` (persistent disk mount) |
| `MAX_RESUME_SIZE_BYTES` | `5242880` |
| `DEMO_SEED_ENABLED` | `false` |
| `VITE_API_URL` | API HTTPS origin, without `/api`; this value is included in the public frontend build and must not contain secrets |

For local development, root `.env.example` contains placeholder values and `frontend/.env.example` leaves `VITE_API_URL` blank so Vite's existing `/api` proxy remains in use. Never copy production credentials into either example file.

## Database migrations and resume storage

Render runs `alembic upgrade head` as the API pre-deploy command before every API release. Render pre-deploy commands require a paid web-service plan. The database URL conversion is applied centrally in backend settings, so both SQLAlchemy and Alembic use `postgresql+psycopg://` with the installed psycopg 3 driver.

Resume PDFs are stored on the local filesystem, not in PostgreSQL. The configured Render persistent disk preserves files across deploys and restarts. It is attached to a single API instance, so keep the API at one instance while this storage design is in use. Disk-backed deploys have downtime during the instance swap and the disk has a fixed 1 GB capacity in this configuration. Monitor usage and move resumes to managed object storage before scaling the API horizontally. Render persistent disks require a paid web-service plan; the free API filesystem is ephemeral and would lose uploaded resumes. Render Postgres's free plan expires after 30 days, so use a paid plan for ongoing production data. [Render disks](https://render.com/docs/disks), [Render Postgres compute plans](https://render.com/docs/blueprint-spec#database-fields).

## Security and operations

- `.env` and `.env.*` are ignored by `.gitignore`; `.env.example` is the explicit exception. `backend/uploads/` is also ignored.
- The backend CORS middleware allows only the configured `FRONTEND_URL`, with explicit methods and headers and no credentialed cookies. The app sends JWTs as bearer authorization headers.
- The API health endpoint is `GET /api/health`. Render probes this endpoint after startup. Migrations must succeed before a deploy proceeds to the API start command.
- Provider timeouts, provider HTTP errors (including rate limits), and malformed AI responses are converted to safe analysis errors. AI credentials remain backend-only. The frontend API timeout is 30 seconds, covering the default 25-second AI provider timeout plus overhead.
- Database credentials, JWT secrets, and AI keys must be entered/generated in Render's environment settings, never committed to the repository.
- The current checkout does not include Git metadata. The working-tree secret scan found no credential-shaped values in source/config files, and `.env` is ignored, but historical commits and remote repository contents must be checked separately. Rotate any credential that was ever committed or shared.

## Local verification commands

From the repository root:

```sh
cd backend
.venv/bin/pytest -q
DATABASE_URL='postgresql+psycopg://<user>:<password>@<host>:5432/<database>' .venv/bin/alembic upgrade head
cd ../frontend
npm ci
npm run build
```

For a production-style local API startup, provide `DATABASE_URL`, `JWT_SECRET_KEY`, `FRONTEND_URL`, and `PORT`, then from `backend/` run:

```sh
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
```

The database migration command above is only safe when pointed at a disposable local/test database. Never use it as a substitute for a backup or run destructive schema commands against production.
