from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import create_app


def get_token(client: TestClient, account: str) -> str:
    response = client.post("/api/auth/demo-login", json={"account": account})
    assert response.status_code == 200
    return response.json()["token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register(client: TestClient, *, email: str, role: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "correct-horse", "name": email, "role": role},
    )
    assert response.status_code == 201
    return response.json()["token"]


def create_event(client: TestClient, org_token: str, *, starts_at: datetime, title: str) -> str:
    ends_at = starts_at + timedelta(hours=3)
    response = client.post(
        "/api/events",
        headers=auth_header(org_token),
        json={
            "title": title,
            "description": "Event tambahan untuk test dashboard",
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "venue": {
                "name": "Venue Tambahan",
                "city": "Jakarta",
                "address": "Jakarta Barat",
            },
            "claim": {
                "step_free_entrance": 1,
                "elevator_or_ramp": 1,
                "accessible_restroom": 1,
                "accessible_seating": 1,
                "rest_area": 1,
                "parking_or_dropoff": 1,
                "walking_distance_m": 100,
            },
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def submit_request(client: TestClient, att_token: str, event_id: str) -> str:
    arrival = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    response = client.post(
        f"/api/events/{event_id}/requests",
        headers=auth_header(att_token),
        json={"arrival_estimate": arrival, "note": "Butuh kursi roda"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def confirm_request(client: TestClient, att_token: str, org_token: str, request_id: str) -> None:
    respond = client.post(
        f"/api/requests/{request_id}/response",
        headers=auth_header(org_token),
        json={"decision": "can_fulfill", "note": "Siap membantu"},
    )
    assert respond.status_code == 200
    confirm = client.post(
        f"/api/requests/{request_id}/confirm",
        headers=auth_header(att_token),
        json={"accepted": True},
    )
    assert confirm.status_code == 200


def test_dashboard_empty_state_for_a_fresh_attendee(seeded_database):
    with TestClient(create_app()) as client:
        token = register(client, email="fresh-attendee@example.com", role="attendee")
        response = client.get("/api/me/dashboard", headers=auth_header(token))
        assert response.status_code == 200
        body = response.json()
        assert body == {
            "pending_requests_count": 0,
            "active_event": None,
            "recent_requests": [],
        }


def test_dashboard_counts_pending_request(seeded_database):
    with TestClient(create_app()) as client:
        att_token = get_token(client, "attendee")
        submit_request(client, att_token, "evt-upcoming-1")

        response = client.get("/api/me/dashboard", headers=auth_header(att_token))
        assert response.status_code == 200
        body = response.json()
        assert body["pending_requests_count"] == 1
        assert len(body["recent_requests"]) == 2  # the new pending + seeded req-past-1
        assert body["active_event"] is None


def test_dashboard_excludes_confirmed_request_on_completed_event(seeded_database):
    # Demo seed already ships req-past-1: attendee u-att-1, confirmed, on
    # evt-past-1 which is seeded completed. This is exactly the "confirmed
    # but the event already happened" case that must not surface as
    # active_event.
    with TestClient(create_app()) as client:
        att_token = get_token(client, "attendee")
        response = client.get("/api/me/dashboard", headers=auth_header(att_token))
        assert response.status_code == 200
        body = response.json()
        assert body["active_event"] is None
        assert body["pending_requests_count"] == 0
        assert [r["id"] for r in body["recent_requests"]] == ["req-past-1"]


def test_dashboard_active_event_matches_direct_match_endpoint(seeded_database):
    with TestClient(create_app()) as client:
        att_token = get_token(client, "attendee")
        org_token = get_token(client, "organizer")

        request_id = submit_request(client, att_token, "evt-upcoming-1")
        confirm_request(client, att_token, org_token, request_id)

        dashboard = client.get("/api/me/dashboard", headers=auth_header(att_token))
        assert dashboard.status_code == 200
        active = dashboard.json()["active_event"]
        assert active is not None
        assert active["request_id"] == request_id
        assert active["event"]["id"] == "evt-upcoming-1"

        direct_match = client.get(
            "/api/events/evt-upcoming-1/match", headers=auth_header(att_token)
        )
        assert direct_match.status_code == 200
        direct_body = direct_match.json()

        assert active["match"]["score"] == direct_body["score"]
        assert active["match"]["weight_version"] == direct_body["weight_version"]
        assert active["match"]["unknown_attributes"] == direct_body["unknown_attributes"]


def test_dashboard_active_event_picks_the_soonest_upcoming(seeded_database):
    with TestClient(create_app()) as client:
        att_token = get_token(client, "attendee")
        org_token = get_token(client, "organizer")

        # evt-upcoming-1 is seeded starts_at = now + 3 days.
        sooner_starts = datetime.now(timezone.utc) + timedelta(days=1)
        sooner_event_id = create_event(client, org_token, starts_at=sooner_starts, title="Sooner Event")

        first_request_id = submit_request(client, att_token, "evt-upcoming-1")
        confirm_request(client, att_token, org_token, first_request_id)

        second_request_id = submit_request(client, att_token, sooner_event_id)
        confirm_request(client, att_token, org_token, second_request_id)

        dashboard = client.get("/api/me/dashboard", headers=auth_header(att_token))
        assert dashboard.status_code == 200
        active = dashboard.json()["active_event"]
        assert active["event"]["id"] == sooner_event_id
        assert active["request_id"] == second_request_id


def test_dashboard_forbidden_for_organizer(seeded_database):
    with TestClient(create_app()) as client:
        org_token = get_token(client, "organizer")
        response = client.get("/api/me/dashboard", headers=auth_header(org_token))
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "FORBIDDEN"
