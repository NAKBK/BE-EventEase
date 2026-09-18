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

## Project Structure

```text
BE-EventEase/
├── app/
│   ├── core/                  # DB Engine, JWT Security, Error Handlers, Config
│   ├── modules/
│   │   ├── auth/              # Demo Login & Token Issuance (BE-API-001)
│   │   ├── users/             # Attendee Need Profile Models
│   │   ├── organizers/        # Organizer Profile & Ownership
│   │   ├── venues/            # Venue Data & Open Data Sources
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

## License
Distributed under the MIT License for IFEST 2026 Hackathon.
