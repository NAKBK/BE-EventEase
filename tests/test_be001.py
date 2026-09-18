from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.database import get_session_factory
from app.core.dependencies import get_current_user
from app.core.config import get_settings
from app.models import AccessibilityClaim, AccessibilityRequest, Event, User, Venue


def test_migration_and_seed_are_repeatable(seeded_database):
    with get_session_factory()() as session:
        assert session.scalar(select(func.count()).select_from(User)) == 2
        assert session.scalar(select(func.count()).select_from(Venue)) == 2
        assert session.scalar(select(func.count()).select_from(Event)) == 2
        assert session.scalar(select(func.count()).select_from(AccessibilityClaim)) == 2
        assert session.scalar(select(func.count()).select_from(AccessibilityRequest)) == 1
        events = session.scalars(select(Event)).all()
        assert {event.status for event in events} == {"upcoming", "completed"}
        assert {claim.source for claim in session.scalars(select(AccessibilityClaim))} == {
            "demo"
        }
        request = session.get(AccessibilityRequest, "req-past-1")
        assert request.status == "confirmed"


def test_demo_login_contract_and_bearer_rejection(seeded_database):
    from app.main import create_app

    app = create_app()

    @app.get("/_test/protected")
    def protected(user: User = Depends(get_current_user)) -> dict:
        return {"id": user.id, "role": user.role}

    with TestClient(app) as client:
        for account, expected_id, expected_organizer_id in (
            ("attendee", "u-att-1", None),
            ("organizer", "u-org-1", "org-1"),
        ):
            response = client.post("/api/auth/demo-login", json={"account": account})
            assert response.status_code == 200
            body = response.json()
            assert body["user"]["id"] == expected_id
            assert body["user"]["role"] == account
            assert body["user"]["organizer_id"] == expected_organizer_id
            assert isinstance(body["token"], str)
            authorized = client.get(
                "/_test/protected",
                headers={"Authorization": f"Bearer {body['token']}"},
            )
            assert authorized.status_code == 200
            assert authorized.json()["id"] == expected_id

        invalid_account = client.post("/api/auth/demo-login", json={"account": "admin"})
        assert invalid_account.status_code == 422
        assert invalid_account.json()["error"]["code"] == "VALIDATION_ERROR"

        no_token = client.get("/_test/protected")
        assert no_token.status_code == 401
        assert no_token.json()["error"]["code"] == "AUTH_REQUIRED"

        invalid_token = client.get(
            "/_test/protected", headers={"Authorization": "Bearer invalid.token.value"}
        )
        assert invalid_token.status_code == 401
        assert invalid_token.json()["error"]["code"] == "INVALID_TOKEN"

        settings = get_settings()
        expired = jwt.encode(
            {
                "sub": "u-att-1",
                "role": "attendee",
                "iss": settings.jwt_issuer,
                "aud": settings.jwt_audience,
                "iat": datetime.now(timezone.utc) - timedelta(hours=2),
                "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            },
            settings.jwt_secret,
            algorithm="HS256",
        )
        expired_response = client.get(
            "/_test/protected", headers={"Authorization": f"Bearer {expired}"}
        )
        assert expired_response.status_code == 401

        assert client.get("/healthz").json() == {"status": "ok"}


def test_demo_login_can_be_disabled(seeded_database, monkeypatch):
    from app.main import create_app

    monkeypatch.setenv("ENABLE_DEMO_LOGIN", "false")
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        response = client.post("/api/auth/demo-login", json={"account": "organizer"})
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "DEMO_LOGIN_DISABLED"
