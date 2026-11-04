# AroundYou local Docker connection

Verified November 2, 2026:

- Container: `aroundyou-postgres-dev`; volume: `aroundyou-postgres-dev-data`.
- PostgreSQL 16.14, loopback `127.0.0.1:5432`, database `aroundyou`, role `aroundyou_app`.
- Matched backend connection to the setup manifest before migrating; initial public table count was zero.
- Applied existing migrations through `0005`; verified 43 application tables plus Alembic's version table.
- Authenticated FastAPI `/v1/me` passed against this database using an in-process TestClient. This is not a browser/network verification.
- Frontend `.env.local` selects HTTP mode and API `http://127.0.0.1:8000`; existing Vite on port 5173 serves this configuration.
- A sandbox-hosted Uvicorn process reported startup but was unreachable from a separate HTTP client and browser. Host-side startup is pending.
- No live AI calls, provider credentials changes, database reset, volume deletion or fixture changes.

From ordinary Windows PowerShell, run `backend/tools/start_local_runtime.ps1` using its full path. It leaves existing reachable services running, refuses an occupied unverified API port, starts missing servers hidden, provisions only the trusted local development organizer, verifies creation/read through the real HttpAdapter, then opens the browser. It does not mint identities through a public endpoint. The two-hour JWT is passed in a local URL fragment and consumed into sessionStorage; it is not printed or sent as a URL query to a server. This is a trusted development mechanism, not production authentication.

Local URLs after successful host launch:

- React: http://127.0.0.1:5173/create/1
- FastAPI OpenAPI: http://127.0.0.1:8000/docs
- FastAPI process health: http://127.0.0.1:8000/health

The HTTP adapter verification creates an explicitly labeled technical connection-check event, makes no AI request or real community commitment, then reads it through a fresh client. Its result is pending until the host launcher succeeds. Runtime credentials, sessions, logs and Docker manifests remain ignored under backend `.env*` and `.tmp/`. Preserve these files locally; do not commit them. The excluded demo folder remains locally necessary for existing frontend imports.
