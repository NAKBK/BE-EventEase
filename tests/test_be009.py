from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.events import media_controller


def token_for(client: TestClient, account: str) -> str:
    response = client.post("/api/auth/demo-login", json={"account": account})
    assert response.status_code == 200
    return response.json()["token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class FakeStorageClient:
    def __init__(self) -> None:
        self.uploads: list[dict] = []

    def upload(self, path: str, content: bytes, content_type: str) -> str:
        self.uploads.append(
            {"path": path, "content": content, "content_type": content_type}
        )
        return f"https://storage.example/{path}"


def test_organizer_can_upload_image_and_event_detail_lists_media(
    seeded_database, monkeypatch
):
    fake_storage = FakeStorageClient()
    monkeypatch.setattr(
        media_controller,
        "get_storage_client",
        lambda: fake_storage,
    )

    with TestClient(create_app()) as client:
        token = token_for(client, "organizer")
        response = client.post(
            "/api/events/evt-upcoming-1/media",
            headers=auth_header(token),
            files={"file": ("evidence.jpg", b"image bytes", "image/jpeg")},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["event_id"] == "evt-upcoming-1"
        assert body["url"].startswith(
            "https://storage.example/events/evt-upcoming-1/"
        )

        assert fake_storage.uploads == [
            {
                "path": fake_storage.uploads[0]["path"],
                "content": b"image bytes",
                "content_type": "image/jpeg",
            }
        ]
        assert fake_storage.uploads[0]["path"].endswith(".jpg")

        detail = client.get(
            "/api/events/evt-upcoming-1",
            headers=auth_header(token),
        )
        assert detail.status_code == 200
        assert detail.json()["media"] == [body]


def test_non_owner_organizer_upload_is_forbidden(seeded_database):
    with TestClient(create_app()) as client:
        register = client.post(
            "/api/auth/register",
            json={
                "email": "another-organizer@example.com",
                "password": "correct-horse",
                "name": "Another Organizer",
                "role": "organizer",
            },
        )
        assert register.status_code == 201

        response = client.post(
            "/api/events/evt-upcoming-1/media",
            headers=auth_header(register.json()["token"]),
            files={"file": ("evidence.jpg", b"image bytes", "image/jpeg")},
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "FORBIDDEN"


def test_upload_rejects_wrong_content_type(seeded_database):
    with TestClient(create_app()) as client:
        token = token_for(client, "organizer")
        response = client.post(
            "/api/events/evt-upcoming-1/media",
            headers=auth_header(token),
            files={"file": ("notes.txt", b"not an image", "text/plain")},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_upload_rejects_oversized_image(seeded_database):
    with TestClient(create_app()) as client:
        token = token_for(client, "organizer")
        response = client.post(
            "/api/events/evt-upcoming-1/media",
            headers=auth_header(token),
            files={
                "file": (
                    "large.jpg",
                    b"x" * (media_controller.MAX_MEDIA_BYTES + 1),
                    "image/jpeg",
                )
            },
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
