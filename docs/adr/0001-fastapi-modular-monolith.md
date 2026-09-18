# ADR-0001: FastAPI modular monolith

## Context

24-hour hackathon build, two-person-ish team split across a Next.js frontend and
this backend, communicating only through a shared, versioned API contract. The
backend needs: fast iteration, a real relational schema (accessibility requests
and verification have real state machines, not just CRUD), deterministic
server-side scoring (the weighted-sum formula must never run twice with different
results), and a deploy target that doesn't require infrastructure work under time
pressure.

## Decision

Python + FastAPI, organized as a **modular monolith**: one deployable process, one
Postgres database, but code split into `app/modules/<domain>/` packages
(`models.py`/`schemas.py`/`service.py`/`controller.py`) so each domain reads
independently. SQLAlchemy 2.0 (sync engine) + Alembic for schema and migrations.
JWT bearer auth. Deploy target: Render Docker service + Supabase-hosted Postgres.

Rejected alternatives:

- **Microservices** - the domains (needs, events, requests, verification,
  reliability) are tightly coupled through a handful of foreign keys and one shared
  scoring formula; splitting them into services would mean either a distributed
  transaction or an eventually-consistent reliability score, neither of which is
  needed at this scale and both of which cost debugging time the 24-hour budget
  doesn't have.
- **A second Node/Nest backend to match the FE's stack** - matching languages
  buys nothing here since FE and BE only ever talk over the documented HTTP contract;
  optimizing for the contract instead of stack uniformity was the explicit strategy
  agreed for this project.
- **Serverless functions per endpoint** - would fragment the request/verification
  state machine across cold-start boundaries for no benefit at this traffic scale,
  and complicates the single Alembic-managed schema.

## Consequences

- One `alembic upgrade head` and one running process is the whole backend - matches
  the "clean database bootstraps repeatedly" acceptance criterion in BE-001.
- Business logic in `service.py` never imports FastAPI (`Request`/`Response`) -
  every service function is a plain Python function taking a `Session` and
  arguments, raising `app.core.errors.APIError` on failure. This is what let
  `organizers.service.get_organizer_reliability` be called directly from
  `events.service`, `verification.service`, and `organizers.controller` without any
  HTTP round-trip - see ADR-0004.
- Cost: nothing stops one module's service from importing another's models directly
  (e.g. `organizers/service.py` imports `Event` from `events.models`). That's an
  accepted, deliberate monolith trade-off, not an oversight - see
  `docs/playbook.md#adding-a-new-module` for the convention that keeps this
  navigable instead of tangled.
