from fastapi.testclient import TestClient

from app.main import create_app


def get_token(client: TestClient, account: str = "attendee") -> str:
    response = client.post("/api/auth/demo-login", json={"account": account})
    assert response.status_code == 200
    return response.json()["token"]


def test_calculate_match_success(seeded_database):
    app = create_app()
    with TestClient(app) as client:
        token = get_token(client, "attendee")
        response = client.get(
            "/api/events/evt-upcoming-1/match",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["event_id"] == "evt-upcoming-1"
        assert "score" in data
        assert isinstance(data["score"], int)
        assert data["weight_version"] == "provisional-v1"
        assert len(data["breakdown"]) == 7

        unknowns = data["unknown_attributes"]
        assert "accessible_restroom" in unknowns

        # Test past event as well
        response_past = client.get(
            "/api/events/evt-past-1/match",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response_past.status_code == 200
        data_past = response_past.json()
        assert data_past["event_id"] == "evt-past-1"


def test_calculate_match_organizer_forbidden(seeded_database):
    app = create_app()
    with TestClient(app) as client:
        token = get_token(client, "organizer")
        response = client.get(
            "/api/events/evt-upcoming-1/match",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "FORBIDDEN"


def test_calculate_match_event_not_found(seeded_database):
    app = create_app()
    with TestClient(app) as client:
        token = get_token(client, "attendee")
        response = client.get(
            "/api/events/invalid-event-id/match",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "EVENT_NOT_FOUND"
