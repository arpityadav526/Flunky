# Backend operations

Install: `uv sync --extra dev --extra test`.

For a new local database: `uv run alembic upgrade head`, then `uv run uvicorn backend.main:app`.
For a legacy database with users/tasks but no alembic_version: stop the server, make a SQLite backup, confirm the schema matches migration 0001, run `uv run alembic stamp 0001`, then `uv run alembic upgrade head`. Never stamp a blank database.

Canonical API: `/v1/register`, `/v1/login`, `/v1/tasks`. Original routes are compatibility aliases. `/docs` lists the API. Task lists accept `limit` (1–100), `offset`, `sort` (prefix `-` for descending), `completed`, `priority`, `search`, `tag`, `due_before`, `due_after`, `deleted`. `X-Total-Count` reports the filtered total. DELETE soft-deletes; POST `/v1/tasks/{id}/restore` restores. Bulk complete/delete validate every ID before changing any task.

`/health` is process liveness; `/ready` requires database connectivity and the Alembic version table. Apply migrations before serving traffic. All error envelopes include an error code, message, and request ID. Validation errors never echo passwords. The legacy detail field is retained.

Set `ENVIRONMENT=production` and a random `SECRET_KEY` of at least 32 characters. Optional `SENTRY_DSN` enables error reporting with default PII collection disabled. JSON request logs exclude request bodies and query strings.

Docker Compose uses PostgreSQL 16, a one-shot migration service, and a non-root API. Set SECRET_KEY and POSTGRES_PASSWORD in your shell or local .env, then run `docker compose up --build`. Do not commit credentials. If a password contains URL-reserved characters, supply an encoded DATABASE_URL in your deployment configuration. The database is not exposed on a host port.

Implementation references: [SQLAlchemy async sessions](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html), [Alembic async migration recipe](https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic).

## Authentication

Apply migration 0003 before starting the new API. Old stateless JWTs no longer authenticate; sign in again. Successful legacy bcrypt logins rehash the password with Argon2id. Access tokens expire after 15 minutes by default. Refresh tokens rotate on every use; replay revokes the whole session family. `flunky logout --everywhere` revokes all sessions and PATs. PAT creation requires email verification.

`flunky login` starts browser approval; `flunky login --with-password --username alice --password-stdin` reads a script password without exposing it as a process argument. Credentials use the OS keychain. If unavailable, a warning identifies private-file fallback. `FLUNKY_TOKEN_STORAGE=file` explicitly selects fallback; `FLUNKY_CONFIG_DIR` isolates scripted environments. Tokens are scoped to the configured API URL. Expiring access tokens refresh automatically.

Dev email goes to private JSON messages under the platform data directory's mailbox (override `FLUNKY_MAILBOX_DIR`). Console logs contain only the filename. The `Mailer` interface needs a production delivery adapter before public email flows are enabled. The in-memory rate limiter is per process; supply a shared adapter for distributed enforcement. Neither production integration is claimed complete.

Account endpoints under `/v1/auth`: `verify-email`, `resend-verification`, `password-reset`, `password-reset/confirm`, `change-password`, `account`, `tokens`, `logout`, `refresh`, `me`. OpenAPI documents request bodies. Password changes/reset revoke existing sessions and outstanding reset tokens. Account deletion requires the current password.
