from fastapi.testclient import TestClient

from app.main import create_app


VALID_CLAIM = {
    "step_free_entrance": 1,
    "elevator_or_ramp": 1,
    "accessible_restroom": 1,
    "accessible_seating": 1,
    "rest_area": 1,
    "parking_or_dropoff": 1,
    "walking_distance_m": 100,
}

VALID_VENUE = {"name": "Venue Baru", "city": "Jakarta", "address": "Jl. Contoh No. 1"}


def token_for(client: TestClient, role: str) -> str:
    response = client.post("/api/auth/demo-login", json={"account": role})
    assert response.status_code == 200
    return response.json()["token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# GET/PUT /api/me/needs (BE-API-002/003)
# ---------------------------------------------------------------------------


def test_needs_round_trip_for_attendee(seeded_database):
    with TestClient(create_app()) as client:
        token = token_for(client, "attendee")

        get_response = client.get("/api/me/needs", headers=auth_header(token))
        assert get_response.status_code == 200
        assert get_response.json()["profile"]["step_free_entrance"] is True

        payload = {
            "step_free_entrance": False,
            "elevator_or_ramp": False,
            "accessible_restroom": False,
            "accessible_seating": False,
            "rest_area": False,
            "parking_or_dropoff": False,
            "walking_distance": "any",
        }
        put_response = client.put("/api/me/needs", json=payload, headers=auth_header(token))
        assert put_response.status_code == 200
        assert put_response.json()["profile"] == payload

        reread = client.get("/api/me/needs", headers=auth_header(token))
        assert reread.json()["profile"] == payload


def test_needs_requires_auth(seeded_database):
    with TestClient(create_app()) as client:
        assert client.get("/api/me/needs").status_code == 401
        assert client.put("/api/me/needs", json={}).status_code == 401


def test_needs_forbidden_for_organizer(seeded_database):
    """Regression test: shared/API.md BE-API-002/003 require attendee bearer."""
    with TestClient(create_app()) as client:
        token = token_for(client, "organizer")

        get_response = client.get("/api/me/needs", headers=auth_header(token))
        assert get_response.status_code == 403
        assert get_response.json()["error"]["code"] == "FORBIDDEN"

        put_response = client.put(
            "/api/me/needs",
            json={
                "step_free_entrance": True,
                "elevator_or_ramp": True,
                "accessible_restroom": True,
                "accessible_seating": True,
                "rest_area": True,
                "parking_or_dropoff": True,
                "walking_distance": "short",
            },
            headers=auth_header(token),
        )
        assert put_response.status_code == 403
        assert put_response.json()["error"]["code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# GET /api/events (BE-API-004)
# ---------------------------------------------------------------------------


def test_list_events_requires_auth(seeded_database):
    with TestClient(create_app()) as client:
        assert client.get("/api/events").status_code == 401


def test_list_events_filters_and_pagination(seeded_database):
    with TestClient(create_app()) as client:
        token = token_for(client, "attendee")

        all_events = client.get("/api/events", headers=auth_header(token))
        assert all_events.status_code == 200
        assert all_events.json()["total"] == 2

        upcoming_only = client.get(
            "/api/events?status=upcoming", headers=auth_header(token)
        )
        assert upcoming_only.status_code == 200
        assert all(
            item["status"] == "upcoming" for item in upcoming_only.json()["items"]
        )

        paged = client.get("/api/events?limit=1&offset=0", headers=auth_header(token))
        assert len(paged.json()["items"]) == 1
        assert paged.json()["limit"] == 1


def test_attendee_cannot_use_mine_filter(seeded_database):
    with TestClient(create_app()) as client:
        token = token_for(client, "attendee")
        response = client.get("/api/events?mine=true", headers=auth_header(token))
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "FORBIDDEN"


def test_organizer_mine_filter_scopes_to_own_events(seeded_database):
    with TestClient(create_app()) as client:
        token = token_for(client, "organizer")
        response = client.get("/api/events?mine=true", headers=auth_header(token))
        assert response.status_code == 200
        assert response.json()["total"] == 2  # both seeded events belong to org-1


# ---------------------------------------------------------------------------
# GET /api/events/{event_id} (BE-API-005)
# ---------------------------------------------------------------------------


def test_get_event_detail_shape(seeded_database):
    with TestClient(create_app()) as client:
        token = token_for(client, "attendee")
        response = client.get(
            "/api/events/evt-upcoming-1", headers=auth_header(token)
        )
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == "evt-upcoming-1"
        assert body["venue"]["lat"] is None
        assert body["claim"]["source"] == "demo"
        assert body["media"] == []


def test_get_event_not_found(seeded_database):
    with TestClient(create_app()) as client:
        token = token_for(client, "attendee")
        response = client.get("/api/events/does-not-exist", headers=auth_header(token))
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "EVENT_NOT_FOUND"


# ---------------------------------------------------------------------------
# POST /api/events (BE-API-007)
# ---------------------------------------------------------------------------


def test_organizer_can_create_event(seeded_database):
    with TestClient(create_app()) as client:
        token = token_for(client, "organizer")
        response = client.post(
            "/api/events",
            headers=auth_header(token),
            json={
                "title": "Event Baru",
                "description": "Deskripsi",
                "starts_at": "2027-01-01T09:00:00+07:00",
                "ends_at": "2027-01-01T12:00:00+07:00",
                "venue": VALID_VENUE,
                "claim": VALID_CLAIM,
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["claim"]["source"] == "organizer"
        assert body["venue"]["name"] == "Venue Baru"

        # round-trip: newly created event is visible via detail endpoint
        detail = client.get(f"/api/events/{body['id']}", headers=auth_header(token))
        assert detail.status_code == 200


def test_attendee_cannot_create_event(seeded_database):
    with TestClient(create_app()) as client:
        token = token_for(client, "attendee")
        response = client.post(
            "/api/events",
            headers=auth_header(token),
            json={
                "title": "Event Baru",
                "starts_at": "2027-01-01T09:00:00+07:00",
                "ends_at": "2027-01-01T12:00:00+07:00",
                "venue": VALID_VENUE,
                "claim": VALID_CLAIM,
            },
        )
        assert response.status_code == 403


def test_create_event_invalid_dates_rejected(seeded_database):
    with TestClient(create_app()) as client:
        token = token_for(client, "organizer")
        response = client.post(
            "/api/events",
            headers=auth_header(token),
            json={
                "title": "Tanggal salah",
                "starts_at": "2027-01-02T09:00:00+07:00",
                "ends_at": "2027-01-01T09:00:00+07:00",
                "venue": VALID_VENUE,
                "claim": VALID_CLAIM,
            },
        )
        assert response.status_code == 422


def test_create_event_missing_claim_key_rejected(seeded_database):
    """Regression test: claim keys must be sent explicitly (may be null)."""
    with TestClient(create_app()) as client:
        token = token_for(client, "organizer")
        incomplete_claim = {k: v for k, v in VALID_CLAIM.items() if k != "elevator_or_ramp"}
        response = client.post(
            "/api/events",
            headers=auth_header(token),
            json={
                "title": "Claim tidak lengkap",
                "starts_at": "2027-01-01T09:00:00+07:00",
                "ends_at": "2027-01-01T12:00:00+07:00",
                "venue": VALID_VENUE,
                "claim": incomplete_claim,
            },
        )
        assert response.status_code == 422


def test_create_event_out_of_range_coordinates_rejected(seeded_database):
    with TestClient(create_app()) as client:
        token = token_for(client, "organizer")
        response = client.post(
            "/api/events",
            headers=auth_header(token),
            json={
                "title": "Koordinat salah",
                "starts_at": "2027-01-01T09:00:00+07:00",
                "ends_at": "2027-01-01T12:00:00+07:00",
                "venue": {**VALID_VENUE, "lat": 999, "lng": 999},
                "claim": VALID_CLAIM,
            },
        )
        assert response.status_code == 422


def test_newly_registered_organizer_can_create_event(seeded_database):
    """Regression test: register(role=organizer) must auto-provision an Organizer row."""
    with TestClient(create_app()) as client:
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "freshorg@example.com",
                "password": "correct-horse",
                "name": "Fresh Organizer",
                "role": "organizer",
            },
        )
        assert register_response.status_code == 201
        token = register_response.json()["token"]

        response = client.post(
            "/api/events",
            headers=auth_header(token),
            json={
                "title": "Event Dari Organizer Baru",
                "starts_at": "2027-01-01T09:00:00+07:00",
                "ends_at": "2027-01-01T12:00:00+07:00",
                "venue": VALID_VENUE,
                "claim": VALID_CLAIM,
            },
        )
        assert response.status_code == 201
        assert response.json()["organizer"]["name"] == "Fresh Organizer"
