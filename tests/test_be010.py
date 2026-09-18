from fastapi.testclient import TestClient

from app.main import create_app


def token_for(client: TestClient, role: str) -> str:
    response = client.post("/api/auth/demo-login", json={"account": role})
    assert response.status_code == 200
    return response.json()["token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Facility attribute filters — exact match, null never matches
# ---------------------------------------------------------------------------


def test_facility_filter_excludes_non_matching_and_null_claims(seeded_database):
    """
    evt-upcoming-1: elevator_or_ramp=0.5, accessible_restroom=null
    evt-past-1:     elevator_or_ramp=1,   accessible_restroom=1
    """
    with TestClient(create_app()) as client:
        token = token_for(client, "attendee")

        exact_one = client.get(
            "/api/events?elevator_or_ramp=1", headers=auth_header(token)
        )
        assert exact_one.status_code == 200
        ids = {item["id"] for item in exact_one.json()["items"]}
        assert ids == {"evt-past-1"}

        exact_half = client.get(
            "/api/events?elevator_or_ramp=0.5", headers=auth_header(token)
        )
        assert {item["id"] for item in exact_half.json()["items"]} == {"evt-upcoming-1"}

        # accessible_restroom is null on evt-upcoming-1 -> must never match,
        # not even a filter for the "worst" value.
        restroom_filter = client.get(
            "/api/events?accessible_restroom=1", headers=auth_header(token)
        )
        assert {item["id"] for item in restroom_filter.json()["items"]} == {"evt-past-1"}


def test_facility_filter_invalid_value_rejected(seeded_database):
    with TestClient(create_app()) as client:
        token = token_for(client, "attendee")
        response = client.get(
            "/api/events?elevator_or_ramp=0.3", headers=auth_header(token)
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# date_from / date_to
# ---------------------------------------------------------------------------


def test_date_range_filters_events(seeded_database):
    from datetime import date, timedelta

    with TestClient(create_app()) as client:
        token = token_for(client, "attendee")
        today = date.today().isoformat()

        only_future = client.get(
            f"/api/events?date_from={today}", headers=auth_header(token)
        )
        assert only_future.status_code == 200
        assert {item["id"] for item in only_future.json()["items"]} == {"evt-upcoming-1"}

        yesterday = (date.today() - timedelta(days=1)).isoformat()
        only_past = client.get(
            f"/api/events?date_to={yesterday}", headers=auth_header(token)
        )
        assert {item["id"] for item in only_past.json()["items"]} == {"evt-past-1"}


def test_date_from_after_date_to_rejected(seeded_database):
    with TestClient(create_app()) as client:
        token = token_for(client, "attendee")
        response = client.get(
            "/api/events?date_from=2027-01-02&date_to=2027-01-01",
            headers=auth_header(token),
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# sort=match_score
# ---------------------------------------------------------------------------


def test_sort_by_match_score_orders_events_and_reuses_match_formula(seeded_database):
    with TestClient(create_app()) as client:
        token = token_for(client, "attendee")

        listed = client.get(
            "/api/events?sort=match_score", headers=auth_header(token)
        )
        assert listed.status_code == 200
        items = listed.json()["items"]
        assert [item["id"] for item in items] == ["evt-past-1", "evt-upcoming-1"]

        # Regression: the list must reuse BE-API-006's formula exactly, not
        # a separate calculation. There's no score field on the list item
        # shape, so cross-check the ranking against the /match endpoint's
        # actual scores for both events.
        scores = {}
        for event_id in ("evt-past-1", "evt-upcoming-1"):
            match = client.get(
                f"/api/events/{event_id}/match", headers=auth_header(token)
            )
            scores[event_id] = match.json()["score"]
        assert scores["evt-past-1"] > scores["evt-upcoming-1"]
        assert [item["id"] for item in items] == sorted(
            scores, key=lambda k: -scores[k]
        )


def test_sort_match_score_requires_saved_profile(seeded_database):
    with TestClient(create_app()) as client:
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "noprofile@example.com",
                "password": "correct-horse",
                "name": "No Profile",
                "role": "attendee",
            },
        )
        token = register_response.json()["token"]

        response = client.get(
            "/api/events?sort=match_score", headers=auth_header(token)
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "NEED_PROFILE_MISSING"


def test_sort_match_score_forbidden_for_organizer(seeded_database):
    with TestClient(create_app()) as client:
        token = token_for(client, "organizer")
        response = client.get(
            "/api/events?sort=match_score", headers=auth_header(token)
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# Unknown query keys and regression with existing BE-API-004 params
# ---------------------------------------------------------------------------


def test_unknown_query_key_rejected(seeded_database):
    with TestClient(create_app()) as client:
        token = token_for(client, "attendee")
        response = client.get(
            "/api/events?not_a_real_param=1", headers=auth_header(token)
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_existing_filters_still_work_combined_with_new_ones(seeded_database):
    with TestClient(create_app()) as client:
        token = token_for(client, "attendee")
        response = client.get(
            "/api/events?status=upcoming&elevator_or_ramp=0.5&limit=10",
            headers=auth_header(token),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["limit"] == 10
        assert {item["id"] for item in body["items"]} == {"evt-upcoming-1"}
