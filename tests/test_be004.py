from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import create_app


def get_token(client: TestClient, account: str) -> str:
    response = client.post("/api/auth/demo-login", json={"account": account})
    return response.json()["token"]


def test_create_and_list_requests(seeded_database):
    app = create_app()
    with TestClient(app) as client:
        att_token = get_token(client, "attendee")
        org_token = get_token(client, "organizer")

        # Attendee creates a request
        arrival = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        res = client.post(
            "/api/events/evt-upcoming-1/requests",
            headers={"Authorization": f"Bearer {att_token}"},
            json={"arrival_estimate": arrival, "note": "Need help with parking"},
        )
        assert res.status_code == 201
        req_id = res.json()["id"]
        assert res.json()["status"] == "pending"

        # Organizer lists requests
        res_list = client.get(
            "/api/requests", headers={"Authorization": f"Bearer {org_token}"}
        )
        assert res_list.status_code == 200
        data = res_list.json()
        assert len(data["items"]) >= 1
        assert any(r["id"] == req_id for r in data["items"])

        # Organizer responds
        res_resp = client.post(
            f"/api/requests/{req_id}/response",
            headers={"Authorization": f"Bearer {org_token}"},
            json={"decision": "can_fulfill", "note": "Parking is ready"},
        )
        assert res_resp.status_code == 200
        assert res_resp.json()["status"] == "responded"

        # Attendee confirms
        res_conf = client.post(
            f"/api/requests/{req_id}/confirm",
            headers={"Authorization": f"Bearer {att_token}"},
            json={"accepted": True},
        )
        assert res_conf.status_code == 200
        assert res_conf.json()["status"] == "confirmed"

        # Cannot create second active request
        res_dup = client.post(
            "/api/events/evt-upcoming-1/requests",
            headers={"Authorization": f"Bearer {att_token}"},
            json={"arrival_estimate": arrival, "note": "Duplicate"},
        )
        assert res_dup.status_code == 409
        assert res_dup.json()["error"]["code"] == "ACTIVE_REQUEST_EXISTS"
