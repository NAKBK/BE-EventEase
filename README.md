<div align="center">

# EventEase — Backend API Service

[![FastAPI](https://img.shields.io/badge/FastAPI-0.141.1-009688.svg?style=flat&logo=FastAPI)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg?style=flat&logo=Python)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16.0-4169E1.svg?style=flat&logo=PostgreSQL)](https://www.postgresql.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00.svg?style=flat&logo=SQLAlchemy)](https://www.sqlalchemy.org/)

<p align="center">
  EventEase is an inclusive platform that empowers individuals with mobility access needs—such as wheelchair users, crutch users, seniors, pregnant people, and stroller users—to make confident, informed decisions when attending public events.
</p>

</div>

## Problem and Solution

Generic accessibility labels like "Accessible" vs "Not Accessible" omit critical venue details. They fail to communicate whether a step-free entrance exists, if accessible restrooms are available, or how far attendees must walk from a drop-off point to the main venue area.

EventEase solves this gap by bridging personalized attendee needs with organizer venue claims across seven physical accessibility dimensions. The platform computes a transparent 0–100% match score, facilitates two-way accommodation requests prior to the event, and maintains organizer accountability through post-event attendee verifications that update a public reliability score.

## Technical Architecture & Tech Stack

```text
       ┌────────────────┐
       │   Frontend     │
       │ (Next.js / FE) │
       └───────┬────────┘
               │ HTTP / REST API
               ▼
 ┌────────────────────────────┐
 │  BE-EventEase (FastAPI)    │
 │  ├── Core & Security (JWT) │
 │  ├── Match Engine (0-100%) │
 │  └── Module Controllers    │
 └─────────────┬──────────────┘
               │ SQLAlchemy 2.0 / Alembic
               ▼
 ┌────────────────────────────┐
 │   PostgreSQL (Supabase)    │
 └────────────────────────────┘
```

- **Framework:** FastAPI (Python 3.12+)
- **ORM & Database:** SQLAlchemy 2.0 (Sync Engine) + Psycopg 3
- **Migrations:** Alembic
- **Authentication:** JWT Bearer Token (Role-based: `attendee` & `organizer`)
- **Documentation:** Automatic OpenAPI 3.0 (Swagger & ReDoc)

## Key Justification

Short version of decisions a reviewer might otherwise question — full reasoning
(context, alternatives rejected, consequences) lives in [`docs/adr/`](docs/adr/).

- **FastAPI modular monolith, not microservices.** The domains (needs, events,
  requests, verification, reliability) share a handful of foreign keys and one
  scoring formula; splitting them into services would trade a same-process function
  call for a distributed-consistency problem the 24-hour build has no budget for.
  See [ADR-0001](docs/adr/0001-fastapi-modular-monolith.md).
- **Demo-login and real register/login issue the exact same JWT shape.** Downstream
  code (`CurrentUser`) never knows which auth path produced a token, so the demo
  path can never silently diverge from the real one.
  See [ADR-0002](docs/adr/0002-dual-auth-demo-and-real.md).
- **The match score is a documented, versioned formula (`weight_version`), not a
  black box.** No real AHP weights exist yet, so the coefficients are explicitly
  labeled provisional and every response returns all seven breakdown rows —
  including unknown ones — instead of hiding what wasn't claimed.
  See [ADR-0003](docs/adr/0003-provisional-weighted-match-formula.md).
- **Reliability is scored per-organizer, never per-venue or per-event.** The claim
  being verified is an organizational promise ("we'll staff the ramp"), not a fact
  about the building — a venue has no accountable, logged-in owner to attach a
  trust score to, and organizers reuse venues across events. Missing or incomplete
  venue data therefore has zero effect on this score, by construction.
  See [ADR-0004](docs/adr/0004-reliability-scoped-to-organizer.md).
- **Claim evidence photos live in Supabase Storage, never as bytes in Postgres or
  in a JSON body.** The API only ever returns a fetchable URL.
  See [ADR-0005](docs/adr/0005-supabase-storage-for-media.md).

## Quick Start Guide

### 1. System Requirements
- Python `>= 3.12`
- PostgreSQL Database (Local or Supabase)

### 2. Environment & Dependency Setup

Use our automated PowerShell script from the project directory:
```powershell
.\setup_venv.ps1
```

Or perform the manual steps below:
```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Copy environment settings
Copy-Item .env.example .env
```

### 3. Environment Configuration (`.env`)
Edit the `.env` file to configure your database connection and secrets:
```env
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.dspwwdltqhicoxmjvjwj.supabase.co:5432/postgres
JWT_SECRET=super-secret-key-at-least-32-characters-long
ENABLE_DEMO_LOGIN=true
SEED_DEMO_DATA=true
```

### 4. Database Migration & Data Seeding
```powershell
# Run database schema migrations
alembic upgrade head

# Seed initial demo fixtures (Users, Jakarta Events, Accessibility Claims)
python -m app.cli seed
```

### 5. Run Local Development Server
```powershell
uvicorn app.main:app --reload
```

- **Interactive API Docs (Swagger UI):** [`http://localhost:8000/docs`](http://localhost:8000/docs)
- **ReDoc Documentation:** [`http://localhost:8000/redoc`](http://localhost:8000/redoc)
- **Healthcheck Endpoint:** `GET http://localhost:8000/healthz`

## Testing

Run the automated integration test suite to verify migrations, seeding, and demo auth flows:

```powershell
pytest -v
```

50 tests as of this writing, one file per backend task (`tests/test_be00N.py`), run
against a fresh SQLite database per test — no shared state, no dependency on a
running Postgres/Supabase instance.

## Demo / Test Flow

The full product journey — Need → Match → Commit → Verify — walked through as
literal `curl` calls against the seeded demo data (login as both roles, save a
need profile, browse a personalized match score, send and answer an accessibility
request, confirm it, optionally attach evidence, then verify a completed seeded
event and watch the organizer's reliability score update):

**[→ `docs/flows.md`](docs/flows.md)**

Each step there also links to the automated test that covers it, so the same path
can be exercised either by hand or with `pytest -v`.

## Project Structure

```text
BE-EventEase/
├── app/
│   ├── core/                  # DB Engine, JWT Security, Error Handlers, Config
│   ├── modules/
│   │   ├── auth/              # Demo Login & Token Issuance (BE-API-001)
│   │   ├── users/             # Attendee Need Profile Models
│   │   ├── organizers/        # Organizer Profile & Ownership
│   │   ├── venues/            # Venue Model (embedded via events; no own routes)
│   │   ├── events/            # Events & 7-Attribute Accessibility Claims
│   │   ├── accessibility_requests/ # Accommodation Commitments Lifecycle
│   │   └── verification/      # Post-event Attendee Verification
│   ├── seed.py                # Idempotent Seed Fixtures
│   ├── cli.py                 # CLI Seed Command
│   └── main.py                # FastAPI App Initialization & Router Setup
├── migrations/                # Alembic Schema Migrations
├── tests/                     # Pytest Integration Suite
├── requirements.txt           # Python Dependency List
├── setup_venv.ps1             # PowerShell Setup Automation Script
└── start.sh                   # Production Entrypoint Script (Docker/Render)
```

## Documentation

This README is the quick tour. For anything deeper, see [`docs/`](docs/):

1. [Architecture](docs/architecture.md)
2. [API Implementation Status](docs/api-status.md)
3. [Demo & Test Flows](docs/flows.md)
4. [Operations Playbook](docs/playbook.md)
5. [Architecture Decision Records](docs/adr/)
6. [License](LICENSE)
