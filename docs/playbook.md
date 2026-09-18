# Operations playbook

Practical, copy-pasteable procedures. For *why* things are built this way, see
`architecture.md` and `adr/`. For the product journey, see `flows.md`.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env      # then edit DATABASE_URL and JWT_SECRET
alembic upgrade head
python -m app.cli seed
uvicorn app.main:app --reload
```

`.\setup_venv.ps1` automates the first three steps. `DATABASE_URL` can point at a
local Postgres or a Supabase pooler connection string - SQLite also works for tests
(see below) but is not what migrations are written against, so don't run the app
itself against SQLite outside of tests.

## Testing

```powershell
pytest -v
```

The test suite (`tests/conftest.py::seeded_database`) spins up a fresh SQLite file
per test in a temp dir, runs Alembic migrations against it, seeds demo data twice
(to assert idempotency), and tears it down after - no shared state between tests,
no dependency on a running Postgres/Supabase instance. 57 tests as of this writing,
one file per BE task (`tests/test_be00N.py`).

**Windows-specific gotcha:** if pytest's own temp-dir cleanup throws
`PermissionError: [WinError 5] Access is denied` on
`C:\Users\<you>\AppData\Local\Temp\pytest-of-<you>`, it's a stale/locked leftover
from a previous run, unrelated to the code under test. Point `--basetemp` somewhere
you own for that run:

```powershell
pytest -v --basetemp=.pytest_tmp
Remove-Item -Recurse -Force .pytest_tmp, .pytest_cache
```

## Resetting demo data

`app/seed.py::seed_demo_data` is idempotent - it only inserts rows that don't
already exist by ID, and never overwrites a running demo's state. To fully reset,
drop and recreate the schema, then reseed:

```powershell
alembic downgrade base
alembic upgrade head
python -m app.cli seed
```

## Media uploads (BE-009)

Requires a Supabase project with Storage enabled:

1. Supabase dashboard → Storage → create a bucket (default name `claim-evidence`,
   matches `SUPABASE_STORAGE_BUCKET`'s default) and mark it **Public**.
2. Project Settings → API → copy the Project URL into `SUPABASE_URL` and the
   `service_role` secret key into `SUPABASE_SERVICE_ROLE_KEY`. The service-role key
   is server-side only - never expose it to the frontend, never commit it.
3. Without those two env vars set, `POST /api/events/{id}/media` fails closed with
   500 `STORAGE_NOT_CONFIGURED` rather than silently no-op'ing - this is intentional,
   see `app/core/storage.py::get_storage_client`.
4. If `python-multipart` isn't importable in a given environment, the whole media
   router is skipped at boot (`app/main.py`) rather than crashing the app - the
   endpoint then 404s instead of 500ing. This should never happen outside a
   deliberately minimal local install, since `python-multipart` is a pinned
   dependency in `requirements.txt`/`pyproject.toml`.

## Deploying

Target is Render (Docker) + Supabase Postgres, per `render.yaml` and `Dockerfile`.

1. Push to the connected repo/branch; Render builds the `Dockerfile` image.
2. `start.sh` runs on container start, in order: `alembic upgrade head` →
   (if `SEED_DEMO_DATA=true`) `python -m app.cli seed` → `uvicorn`.
3. Required env vars on Render (see `render.yaml`): `DATABASE_URL`, `JWT_SECRET`
   (Render can `generateValue`), `CORS_ORIGINS` (JSON array of exact FE origins -
   `app/main.py` wires this straight into `CORSMiddleware`), `ENABLE_DEMO_LOGIN`,
   `SEED_DEMO_DATA`.
4. Render's health check hits `/healthz`, which does a real `SELECT 1` against the
   database - a build that boots but can't reach Postgres will correctly fail health
   checks (503 `DATABASE_UNAVAILABLE`) instead of reporting healthy.
5. Not yet verified end-to-end against a live Render+Supabase pair as of this audit
   (2026-09-18). Treat a first real deploy as its own task, not an assumed-working
   side effect of merging code.

## Adding a new module

Follow the existing shape so every module reads the same way:

1. `app/modules/<name>/models.py`, SQLAlchemy `Base` subclasses only. Skip this
   (and step 2-3) entirely if the module owns no new persisted table and only
   composes other modules' existing reads, the way `app/modules/dashboard/` does
   (no `models.py` at all there, service.py only).
2. Add the new models to `app/models.py`'s imports/`__all__` so Alembic
   autogenerate sees them.
3. `alembic revision --autogenerate -m "<description>"`, then **read the generated
   migration** before applying it, autogenerate is a starting point, not ground
   truth.
4. `schemas.py` (Pydantic), `service.py` (business logic, takes a `Session` and
   plain args, raises `APIError`, never touches `Request`/`Response`),
   `controller.py` (`APIRouter`, role guard via `CurrentUser.role`, delegates to
   `service.py`).
5. Mount the router in `app/main.py` under the agreed URL prefix for that resource.
6. Add `tests/test_<task-id>.py` using the `seeded_database` fixture, copy the
   `token_for`/`auth_header` helpers already duplicated across the existing test
   files rather than inventing new ones.
7. Update `docs/api-status.md` (this repo's own status table) in the same change,
   a status-table edit that doesn't ship with the code that implements it is exactly
   how the existing BE-007 gap went untracked for a while (see `docs/api-status.md`).
8. If the new service calls a helper that lives in another module's `service.py`,
   that helper's name must not start with `_`, an underscore-prefixed name reused
   across a module boundary is a signal that was left in the wrong place, not a
   convention to copy (`map_request_response` and `build_event_list_item` were
   promoted from private to public for exactly this reason when `dashboard/` was
   added).

## Known gaps at a glance

Full detail in `docs/api-status.md`. Short version: BE-API-016 (Jakarta open data
import, BE-007) has no implementation at all - no code, no tests. Everything else
documented for this backend is implemented and covered by tests.
