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


def register(client: TestClient, *, email: str, role: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "correct-horse",
            "name": email,
            "role": role,
        },
    )
    assert response.status_code == 201
    return response.json()["token"]


def test_respond_forbidden_for_non_owning_organizer(seeded_database):
    app = create_app()
    with TestClient(app) as client:
        att_token = get_token(client, "attendee")
        outsider_org_token = register(
            client, email="outsider-org@example.com", role="organizer"
        )

        arrival = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        req_id = client.post(
            "/api/events/evt-upcoming-1/requests",
            headers={"Authorization": f"Bearer {att_token}"},
            json={"arrival_estimate": arrival, "note": "Need help with parking"},
        ).json()["id"]

        res = client.post(
            f"/api/requests/{req_id}/response",
            headers={"Authorization": f"Bearer {outsider_org_token}"},
            json={"decision": "can_fulfill", "note": "Not my event"},
        )
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "FORBIDDEN"


def test_cannot_fulfill_decision_closes_request_without_attendee_confirmation(
    seeded_database,
):
    app = create_app()
    with TestClient(app) as client:
        att_token = get_token(client, "attendee")
        org_token = get_token(client, "organizer")

        arrival = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        req_id = client.post(
            "/api/events/evt-upcoming-1/requests",
            headers={"Authorization": f"Bearer {att_token}"},
            json={"arrival_estimate": arrival, "note": "Need a ramp"},
        ).json()["id"]

        res_resp = client.post(
            f"/api/requests/{req_id}/response",
            headers={"Authorization": f"Bearer {org_token}"},
            json={"decision": "cannot_fulfill", "note": "No ramp available"},
        )
        assert res_resp.status_code == 200
        assert res_resp.json()["status"] == "closed"

        # A closed request is not in the "responded" state, so the attendee
        # can no longer confirm it.
        res_conf = client.post(
            f"/api/requests/{req_id}/confirm",
            headers={"Authorization": f"Bearer {att_token}"},
            json={"accepted": True},
        )
        assert res_conf.status_code == 409
        assert res_conf.json()["error"]["code"] == "INVALID_REQUEST_STATE"


def test_role_guards_on_request_endpoints(seeded_database):
    app = create_app()
    with TestClient(app) as client:
        att_token = get_token(client, "attendee")
        org_token = get_token(client, "organizer")

        arrival = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()

        # Organizer cannot create a request.
        res_create = client.post(
            "/api/events/evt-upcoming-1/requests",
            headers={"Authorization": f"Bearer {org_token}"},
            json={"arrival_estimate": arrival, "note": "Wrong role"},
        )
        assert res_create.status_code == 403
        assert res_create.json()["error"]["code"] == "FORBIDDEN"

        req_id = client.post(
            "/api/events/evt-upcoming-1/requests",
            headers={"Authorization": f"Bearer {att_token}"},
            json={"arrival_estimate": arrival, "note": "Need help"},
        ).json()["id"]

        # Attendee cannot respond as an organizer.
        res_respond = client.post(
            f"/api/requests/{req_id}/response",
            headers={"Authorization": f"Bearer {att_token}"},
            json={"decision": "can_fulfill", "note": "Wrong role"},
        )
        assert res_respond.status_code == 403
        assert res_respond.json()["error"]["code"] == "FORBIDDEN"

        client.post(
            f"/api/requests/{req_id}/response",
            headers={"Authorization": f"Bearer {org_token}"},
            json={"decision": "can_fulfill", "note": "Ready"},
        )

        # Organizer cannot confirm as an attendee.
        res_confirm = client.post(
            f"/api/requests/{req_id}/confirm",
            headers={"Authorization": f"Bearer {org_token}"},
            json={"accepted": True},
        )
        assert res_confirm.status_code == 403
        assert res_confirm.json()["error"]["code"] == "FORBIDDEN"


def test_create_request_rejected_for_non_upcoming_event(seeded_database):
    app = create_app()
    with TestClient(app) as client:
        att_token = get_token(client, "attendee")
        arrival = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()

        res = client.post(
            "/api/events/evt-past-1/requests",
            headers={"Authorization": f"Bearer {att_token}"},
            json={"arrival_estimate": arrival, "note": "Event already over"},
        )
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "EVENT_NOT_UPCOMING"


def test_create_request_requires_saved_need_profile(seeded_database):
    app = create_app()
    with TestClient(app) as client:
        token = register(client, email="noprofile-attendee@example.com", role="attendee")
        arrival = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()

        res = client.post(
            "/api/events/evt-upcoming-1/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={"arrival_estimate": arrival, "note": "No profile yet"},
        )
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "NEED_PROFILE_MISSING"
