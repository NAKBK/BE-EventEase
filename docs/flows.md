# Demo & test flow walkthrough

This is the product's core "Need → Match → Commit → Verify" journey, spelled out as
literal HTTP calls against a locally seeded database. Useful for a live demo, for
manually poking the API, or as a reading guide before touching
`accessibility_requests` or `verification`.

Prerequisite: server running locally (`docs/playbook.md#run-locally`) with
`ENABLE_DEMO_LOGIN=true` and the demo seed loaded. All examples use seeded IDs:
`evt-upcoming-1` (status `upcoming`) and `evt-past-1` (status `completed`).

## 1. Log in as both demo roles

```bash
curl -s -X POST localhost:8000/api/auth/demo-login -H "Content-Type: application/json" \
  -d '{"account":"attendee"}' | tee attendee.json
curl -s -X POST localhost:8000/api/auth/demo-login -H "Content-Type: application/json" \
  -d '{"account":"organizer"}' | tee organizer.json

ATT_TOKEN=$(jq -r .token attendee.json)
ORG_TOKEN=$(jq -r .token organizer.json)
```

Both return the exact same `{token, user}` shape a real `/api/auth/login` would.

## 2. Attendee sets a need profile

```bash
curl -s -X PUT localhost:8000/api/me/needs -H "Authorization: Bearer $ATT_TOKEN" \
  -H "Content-Type: application/json" -d '{
    "step_free_entrance": true, "elevator_or_ramp": true,
    "accessible_restroom": true, "accessible_seating": false,
    "rest_area": false, "parking_or_dropoff": true,
    "walking_distance": "short"
  }'
```

This is a prerequisite for both `sort=match_score` (BE-API-018) and
`GET /events/{id}/match` (BE-API-006) — both return 409 `NEED_PROFILE_MISSING`
without a saved profile.

## 3. Browse events with a personalized score

```bash
curl -s "localhost:8000/api/events?sort=match_score" -H "Authorization: Bearer $ATT_TOKEN"
curl -s localhost:8000/api/events/evt-upcoming-1/match -H "Authorization: Bearer $ATT_TOKEN"
```

The second call returns the full seven-attribute breakdown (`fulfillment`,
`weight`, `label`) — this is what should be rendered as the "why this score"
explanation, per the product rule that a score is never shown without its
breakdown and unknowns.

## 4. Attendee sends an accessibility request

```bash
curl -s -X POST localhost:8000/api/events/evt-upcoming-1/requests \
  -H "Authorization: Bearer $ATT_TOKEN" -H "Content-Type: application/json" -d '{
    "arrival_estimate": "2026-12-01T09:00:00+07:00",
    "note": "Butuh bantuan parkir dan kursi roda"
  }' | tee request.json

REQUEST_ID=$(jq -r .id request.json)
```

Trying to submit a second active request for the same event now returns 409
`ACTIVE_REQUEST_EXISTS` — see `tests/test_be004.py`.

## 5. Organizer responds

```bash
curl -s -X POST localhost:8000/api/requests/$REQUEST_ID/response \
  -H "Authorization: Bearer $ORG_TOKEN" -H "Content-Type: application/json" -d '{
    "decision": "can_fulfill",
    "note": "Parkir difabel tersedia di sisi utara, siap membantu"
  }'
```

`decision: cannot_fulfill` would instead move the request straight to `closed` — no
attendee confirmation step follows a rejection.

## 6. Attendee confirms

```bash
curl -s -X POST localhost:8000/api/requests/$REQUEST_ID/confirm \
  -H "Authorization: Bearer $ATT_TOKEN" -H "Content-Type: application/json" \
  -d '{"accepted": true}'
```

Request is now `confirmed`. Both attendee (`GET /api/requests`) and organizer see the
identical saved state and note — nothing here is private to one side.

## 7. Organizer attaches evidence (optional, BE-009)

```bash
curl -s -X POST localhost:8000/api/events/evt-upcoming-1/media \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -F "file=@ramp-photo.jpg;type=image/jpeg"
```

Requires `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` configured — see
`docs/playbook.md#media-uploads`. Shows up immediately in
`GET /api/events/evt-upcoming-1`'s `media` array.

## 8. Post-event verification (uses the seeded *past* event)

The demo seed already has a `confirmed` request (`req-past-1`) against
`evt-past-1`, which is seeded `completed` and in the past — so this step doesn't
need steps 4-6 repeated:

```bash
curl -s -X POST localhost:8000/api/requests/req-past-1/verification \
  -H "Authorization: Bearer $ATT_TOKEN" -H "Content-Type: application/json" -d '{
    "attributes": {
      "step_free_entrance": "fulfilled",
      "elevator_or_ramp": "fulfilled",
      "accessible_restroom": "partially_fulfilled",
      "accessible_seating": "fulfilled",
      "rest_area": "fulfilled",
      "parking_or_dropoff": "partially_fulfilled",
      "walking_distance": "fulfilled"
    }
  }'
```

The response includes `organizer_reliability` computed fresh — compare it against:

```bash
curl -s localhost:8000/api/organizers/org-1 -H "Authorization: Bearer $ATT_TOKEN"
```

Trying to verify `evt-upcoming-1`'s request instead fails with 409
`EVENT_NOT_COMPLETED` — the event hasn't happened yet. Trying to verify the same
request twice fails with 409 `ALREADY_VERIFIED`.

## Automated equivalent

Every step above has a corresponding assertion in the test suite — this walkthrough
has no logic the tests don't already cover, it's just the same paths in a form you
can read out loud during a demo:

| Step | Test |
| --- | --- |
| 1 | `tests/test_be001.py` |
| 2 | `tests/test_be002.py::test_needs_round_trip_for_attendee` |
| 3 | `tests/test_be003.py`, `tests/test_be010.py::test_sort_by_match_score_orders_events_and_reuses_match_formula` |
| 4 | `tests/test_be004.py::test_create_and_list_requests` |
| 5 | `tests/test_be004.py::test_cannot_fulfill_decision_closes_request_without_attendee_confirmation` |
| 6 | `tests/test_be004.py::test_create_and_list_requests` |
| 7 | `tests/test_be009.py` |
| 8 | `tests/test_be005.py::test_submit_verification_updates_reliability` |

Run the whole thing with `pytest -v` (see `docs/playbook.md#testing`).
