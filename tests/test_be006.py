from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import get_session_factory
from app.models import User


def test_register_then_login(seeded_database):
    from app.main import create_app

    with TestClient(create_app()) as client:
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "New.User@Example.com",
                "password": "correct-horse",
                "name": "New User",
                "role": "attendee",
            },
        )
        assert register_response.status_code == 201
        body = register_response.json()
        assert body["user"]["role"] == "attendee"
        assert isinstance(body["token"], str)

        with get_session_factory()() as session:
            stored = session.execute(
                select(User).where(User.email == "new.user@example.com")
            ).scalar_one()
            assert stored.password_hash != "correct-horse"
            assert stored.password_hash.startswith("pbkdf2_sha256$")

        login_response = client.post(
            "/api/auth/login",
            json={"email": "new.user@example.com", "password": "correct-horse"},
        )
        assert login_response.status_code == 200
        assert login_response.json()["user"]["id"] == body["user"]["id"]


def test_register_duplicate_email_rejected(seeded_database):
    from app.main import create_app

    with TestClient(create_app()) as client:
        payload = {
            "email": "dupe@example.com",
            "password": "correct-horse",
            "name": "Dupe One",
            "role": "attendee",
        }
        first = client.post("/api/auth/register", json=payload)
        assert first.status_code == 201

        second = client.post("/api/auth/register", json={**payload, "name": "Dupe Two"})
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "EMAIL_TAKEN"


def test_login_wrong_password_and_unknown_email(seeded_database):
    from app.main import create_app

    with TestClient(create_app()) as client:
        client.post(
            "/api/auth/register",
            json={
                "email": "known@example.com",
                "password": "correct-horse",
                "name": "Known User",
                "role": "organizer",
            },
        )

        wrong_password = client.post(
            "/api/auth/login",
            json={"email": "known@example.com", "password": "wrong-password"},
        )
        assert wrong_password.status_code == 401
        assert wrong_password.json()["error"]["code"] == "INVALID_CREDENTIALS"

        unknown_email = client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "correct-horse"},
        )
        assert unknown_email.status_code == 401
        assert unknown_email.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_register_validation_errors(seeded_database):
    from app.main import create_app

    with TestClient(create_app()) as client:
        weak_password = client.post(
            "/api/auth/register",
            json={
                "email": "weak@example.com",
                "password": "short",
                "name": "Weak Pw",
                "role": "attendee",
            },
        )
        assert weak_password.status_code == 422
        assert weak_password.json()["error"]["code"] == "VALIDATION_ERROR"

        bad_email = client.post(
            "/api/auth/register",
            json={
                "email": "not-an-email",
                "password": "correct-horse",
                "name": "Bad Email",
                "role": "attendee",
            },
        )
        assert bad_email.status_code == 422

        bad_role = client.post(
            "/api/auth/register",
            json={
                "email": "role@example.com",
                "password": "correct-horse",
                "name": "Bad Role",
                "role": "admin",
            },
        )
        assert bad_role.status_code == 422


def test_real_login_token_works_like_demo_token(seeded_database):
    from fastapi import Depends
    from app.core.dependencies import get_current_user
    from app.main import create_app

    app = create_app()

    @app.get("/_test/protected")
    def protected(user: User = Depends(get_current_user)) -> dict:
        return {"id": user.id, "role": user.role}

    with TestClient(app) as client:
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "protected@example.com",
                "password": "correct-horse",
                "name": "Protected User",
                "role": "attendee",
            },
        )
        token = register_response.json()["token"]
        response = client.get(
            "/_test/protected", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["role"] == "attendee"

        # demo-login continues to work unchanged alongside real auth.
        demo_response = client.post("/api/auth/demo-login", json={"account": "attendee"})
        assert demo_response.status_code == 200
