# API implementation status

This table is the audit trail for every endpoint this backend exposes: what exists,
where the code lives, and what test covers it. Re-check this table whenever an
endpoint's implementation changes.

Last verified: 2026-09-18, against `57 passed` on the full `pytest` suite.

| ID | Endpoint | Task | Status | Code | Tests |
| --- | --- | --- | --- | --- | --- |
| BE-API-001 | `POST /api/auth/demo-login` | BE-001 | Done | `app/modules/auth/controller.py`, `service.py` | `tests/test_be001.py` |
| BE-API-002 | `GET /api/me/needs` | BE-002 | Done | `app/modules/users/controller.py` | `tests/test_be002.py` |
| BE-API-003 | `PUT /api/me/needs` | BE-002 | Done | `app/modules/users/controller.py` | `tests/test_be002.py` |
| BE-API-004 | `GET /api/events` | BE-002 (+ BE-010 extension) | Done | `app/modules/events/controller.py`, `service.py` | `tests/test_be002.py`, `tests/test_be010.py` |
| BE-API-005 | `GET /api/events/{id}` | BE-002 (+ BE-009 `media`, venue `lat`/`lng`) | Done | `app/modules/events/controller.py`, `service.py` | `tests/test_be002.py`, `tests/test_be009.py` |
| BE-API-006 | `GET /api/events/{id}/match` | BE-003 | Done | `app/modules/events/service.py::calculate_match`/`_compute_match` | `tests/test_be003.py`, cross-checked in `tests/test_be010.py` |
| BE-API-007 | `POST /api/events` | BE-002 | Done | `app/modules/events/controller.py::post_event` | `tests/test_be002.py` |
| BE-API-008 | `POST /api/events/{id}/requests` | BE-004 | Done | `app/modules/accessibility_requests/controller.py`, `service.py` | `tests/test_be004.py` |
| BE-API-009 | `GET /api/requests` | BE-004 | Done | same module, `list_requests` | `tests/test_be004.py` |
| BE-API-010 | `POST /api/requests/{id}/response` | BE-004 | Done | same module, `respond_to_request` | `tests/test_be004.py` |
| BE-API-011 | `POST /api/requests/{id}/confirm` | BE-004 | Done | same module, `confirm_response` | `tests/test_be004.py` |
| BE-API-012 | `POST /api/requests/{id}/verification` | BE-005 | Done | `app/modules/verification/controller.py`, `service.py` | `tests/test_be005.py` |
| BE-API-013 | `GET /api/organizers/{id}` | BE-005 | Done | `app/modules/organizers/controller.py`, `service.py::get_organizer_reliability` | `tests/test_be005.py` |
| BE-API-014 | `POST /api/auth/register` | BE-006 | Done | `app/modules/auth/controller.py`, `service.py::register_user` | `tests/test_be006.py` |
| BE-API-015 | `POST /api/auth/login` | BE-006 | Done | same module, `login_user` | `tests/test_be006.py` |
| BE-API-016 | `POST /api/admin/import/dki-open-data` | BE-007 | **Not started** | none - no `admin` module, no import script | none |
| BE-API-017 | `POST /api/events/{id}/media` | BE-009 | Done | `app/modules/events/media_controller.py` | `tests/test_be009.py` |
| BE-API-018 | `GET /api/events` (extended filters/sort) | BE-010 | Done | `app/modules/events/controller.py`/`service.py` (shares BE-API-004's handler) | `tests/test_be010.py` |
| - (extension) | Venue `lat`/`lng` on venue embeds | BE-002 | Done | `app/modules/events/service.py::_build_venue_embed`, `app/modules/venues/models.py` | `tests/test_be002.py` |
| BE-API-019 | `GET /api/me/dashboard` | BE-011 | Done | `app/modules/dashboard/controller.py`, `service.py` (composes `accessibility_requests`/`events` services only, no new business logic) | `tests/test_be011.py` |

## What "Done" means here

Every row marked Done has: the route wired in `app/main.py`, request/response
schemas matching the documented wire contract exactly (checked field-by-field during
this audit), the documented error codes, and at least one automated HTTP-level test
exercising the success path and its main failure modes. It does **not** mean
deployed - see [`playbook.md`](playbook.md#deploying) for what's still manual before
a real Render/Supabase deploy.

## Gap: BE-API-016 / BE-007 - Jakarta open data import

This is the only P0/P1-adjacent contract endpoint with **zero implementation**:

- No `app/modules/admin` (or equivalent) package exists.
- No dataset fetch/parse/mapping code exists anywhere in `app/`.
- No `source="open_data"` value is ever written by any current code path - every
  seeded/created row today is `source="demo"` or `source="organizer"`.
- No test file (`tests/test_be007.py` does not exist).

It depends only on BE-002 (done), so it is unblocked and ready to start whenever
picked up.
