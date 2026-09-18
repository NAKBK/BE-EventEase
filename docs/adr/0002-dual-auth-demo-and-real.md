# ADR-0002: Demo-login and real register/login coexist

## Context

BE-001 needed a working end-to-end demo before real user accounts existed — the
demo login issues JWTs to seeded synthetic accounts and was never meant to be
real-user authentication. Later, BE-006 added real registration/login
(BE-API-014/015) so the product isn't permanently locked to two hardcoded
accounts. Both had to work at the same time: the demo must keep working for
rehearsals and grading, and real accounts must work identically for anything
built on top of auth.

## Decision

Three ways to obtain a bearer token, all producing the **exact same JWT shape**
(`sub`, `role`, `iss`, `aud`, `iat`, `exp` — `app/core/security.py::create_access_token`):

1. `POST /api/auth/demo-login` (`app/modules/auth/service.py::demo_login`) — looks up
   one of two hardcoded seeded user IDs, gated by `ENABLE_DEMO_LOGIN`. Refuses to
   issue a token if the seed is missing (`DEMO_DATA_MISSING`, 503) rather than
   fabricating a user.
2. `POST /api/auth/register` — creates a real `User` row with a PBKDF2-hashed
   password. If `role == "organizer"`, it **also** creates the matching `Organizer`
   row in the same transaction (`register_user`, `app/modules/auth/service.py`) —
   without this, a real organizer account would hit `NOT_AN_ORGANIZER` (403) the
   first time they tried to publish an event, since ownership is resolved through
   `Organizer.owner_user_id`, not the `User` row directly.
3. `POST /api/auth/login` — verifies the PBKDF2 hash and issues the same token.

Every downstream endpoint (`CurrentUser` in `app/core/dependencies.py`) only ever
looks at the decoded JWT's `sub`/`role` plus the matching `User` row — it has no
idea which of the three paths produced the token, by construction.

## Consequences

- Demo rehearsals and the real signup flow can never drift apart, because there's
  only one code path downstream of "I have a valid token." A test verifies this
  directly (`tests/test_be006.py::test_real_login_token_works_like_demo_token`).
- Passwords are never logged or stored in plaintext — `hash_password` always salts
  (`secrets.token_hex(16)`) and uses 260k PBKDF2-HMAC-SHA256 iterations; `verify_password`
  uses `hmac.compare_digest` for the comparison, not `==`, to avoid a timing
  side-channel.
- Demo accounts have no `password_hash` (`login_user` rejects them with
  `INVALID_CREDENTIALS` if someone tries `/login` with a demo email) — the demo
  path and the real path are two distinct issuance routes into the same token
  shape, not two authentication mechanisms layered on each other.
- `ENABLE_DEMO_LOGIN` is a deploy-time kill switch (`.env.example`: "keep false when
  this API holds real users or data") — it is expected to be flipped off once this
  stops being a hackathon demo, without touching the real auth code path at all.
