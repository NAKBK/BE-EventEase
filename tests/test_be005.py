from fastapi.testclient import TestClient

from app.main import create_app


def get_token(client: TestClient, account: str) -> str:
    response = client.post("/api/auth/demo-login", json={"account": account})
    assert response.status_code == 200
    return response.json()["token"]


ATTRIBUTES = {
    "step_free_entrance": "fulfilled",
    "elevator_or_ramp": "partially_fulfilled",
    "accessible_restroom": "not_fulfilled",
    "accessible_seating": "fulfilled",
    "rest_area": "fulfilled",
    "parking_or_dropoff": "partially_fulfilled",
    "walking_distance": "fulfilled",
}


def test_submit_verification_updates_reliability(seeded_database):
    with TestClient(create_app()) as client:
        attendee_token = get_token(client, "attendee")
        organizer_token = get_token(client, "organizer")

        response = client.post(
            "/api/requests/req-past-1/verification",
            headers={"Authorization": f"Bearer {attendee_token}"},
            json={"attributes": ATTRIBUTES},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["request_id"] == "req-past-1"
        assert data["status"] == "verified"
        assert data["organizer_reliability"] == {
            "score": 71,
            "sample_count": 1,
            "window_size": 20,
            "updated_at": data["submitted_at"],
        }

        profile = client.get(
            "/api/organizers/org-1",
            headers={"Authorization": f"Bearer {organizer_token}"},
        )
        assert profile.status_code == 200
        assert profile.json()["reliability"]["score"] == 71

        duplicate = client.post(
            "/api/requests/req-past-1/verification",
            headers={"Authorization": f"Bearer {attendee_token}"},
            json={"attributes": ATTRIBUTES},
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "ALREADY_VERIFIED"


def test_verification_requires_all_attributes(seeded_database):
    with TestClient(create_app()) as client:
        attendee_token = get_token(client, "attendee")
        incomplete = {key: value for key, value in ATTRIBUTES.items() if key != "walking_distance"}
        response = client.post(
            "/api/requests/req-past-1/verification",
            headers={"Authorization": f"Bearer {attendee_token}"},
            json={"attributes": incomplete},
        )
        assert response.status_code == 422
