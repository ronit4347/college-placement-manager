# Database foundation

The placement API uses PostgreSQL through SQLAlchemy. Configure `DATABASE_URL` in the root `.env` for local development; production receives it from the hosting provider. Alembic migrations live under `backend/migrations/` and are applied with `alembic upgrade head`. The `/api/health` endpoint intentionally reports process health without querying the database, so verify migrations/database connectivity separately. See [docs/database.md](../docs/database.md) for schema details and [docs/deployment-render.md](../docs/deployment-render.md) for the Render configuration.
