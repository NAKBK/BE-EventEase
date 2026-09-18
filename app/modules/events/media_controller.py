"""BE-009 / BE-API-017: POST /api/events/{event_id}/media."""

from datetime import datetime, timezone
import mimetypes
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, File, UploadFile
import httpx
from sqlalchemy import select

from app.core.dependencies import CurrentUser, SessionDep
from app.core.errors import APIError
from app.core.storage import StorageNotConfigured, get_storage_client
from app.modules.events.models import Event, EventMedia
from app.modules.events.schemas import MediaItem
from app.modules.organizers.models import Organizer


router = APIRouter(tags=["events"])

MAX_MEDIA_BYTES = 5 * 1024 * 1024


def _validate_image(file: UploadFile) -> str:
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise APIError(
            422,
            "VALIDATION_ERROR",
            "File harus berupa gambar",
            {"field": "file", "reason": "content_type"},
        )
    return content_type


def _read_limited_file(file: UploadFile) -> bytes:
    content = file.file.read(MAX_MEDIA_BYTES + 1)
    if len(content) > MAX_MEDIA_BYTES:
        raise APIError(
            422,
            "VALIDATION_ERROR",
            "Ukuran file melebihi batas 5 MB",
            {"field": "file", "reason": "max_size", "max_bytes": MAX_MEDIA_BYTES},
        )
    if not content:
        raise APIError(
            422,
            "VALIDATION_ERROR",
            "File tidak boleh kosong",
            {"field": "file", "reason": "empty"},
        )
    return content


def _storage_path(event_id: str, filename: str | None, content_type: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    if not suffix or len(suffix) > 12:
        suffix = mimetypes.guess_extension(content_type) or ".img"
    return f"events/{event_id}/{uuid4().hex}{suffix}"


@router.post("/{event_id}/media", response_model=MediaItem, status_code=201)
def upload_event_media(
    event_id: str,
    session: SessionDep,
    current_user: CurrentUser,
    file: Annotated[UploadFile, File(description="Image file (image/* only, max 5 MB)")],
) -> MediaItem:
    """
    BE-API-017: Attach one photo as accessibility claim evidence.
    Requires owning organizer bearer.
    """
    if current_user.role != "organizer":
        raise APIError(403, "FORBIDDEN", "Hanya organizer yang dapat mengunggah media event")

    event = session.get(Event, event_id)
    if event is None:
        raise APIError(404, "EVENT_NOT_FOUND", f"Event '{event_id}' tidak ditemukan")

    organizer = session.scalar(
        select(Organizer).where(Organizer.owner_user_id == current_user.id)
    )
    if organizer is None or organizer.id != event.organizer_id:
        raise APIError(403, "FORBIDDEN", "Anda bukan pemilik event ini")

    content_type = _validate_image(file)
    content = _read_limited_file(file)
    path = _storage_path(event_id, file.filename, content_type)

    try:
        url = get_storage_client().upload(path, content, content_type)
    except StorageNotConfigured as exc:
        raise APIError(
            500,
            "STORAGE_NOT_CONFIGURED",
            "Konfigurasi penyimpanan media belum tersedia",
        ) from exc
    except httpx.HTTPError as exc:
        raise APIError(
            500,
            "MEDIA_UPLOAD_FAILED",
            "Gagal mengunggah media",
        ) from exc

    media = EventMedia(
        id=str(uuid4()),
        event_id=event.id,
        uploader_id=current_user.id,
        url=url,
        uploaded_at=datetime.now(timezone.utc),
    )
    session.add(media)
    session.commit()
    session.refresh(media)
    return MediaItem.model_validate(media)
