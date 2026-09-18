"""BE-009 / BE-API-017: POST /api/events/{event_id}/media

Upload a photo as accessibility claim evidence.

Current status: stub — returns 501 until Supabase Storage is wired in BE-009.
The endpoint shape, auth, and error codes are already contract-correct so FE
can code against this path from BE-002 onwards.

Full implementation (BE-009) will:
  1. validate content-type (image/* only) and file size (≤ 5 MB).
  2. upload to Supabase Storage via app/core/storage.py.
  3. persist EventMedia row and return MediaItem JSON.
"""

from typing import Annotated

from fastapi import APIRouter, File, UploadFile

from app.core.dependencies import CurrentUser, SessionDep
from app.core.errors import APIError
from app.modules.events.models import Event
from app.modules.events.schemas import MediaItem


router = APIRouter(tags=["events"])


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

    Returns 501 until BE-009 wires Supabase Storage.
    Auth and ownership checks are enforced now so FE integration can run.
    """
    if current_user.role != "organizer":
        raise APIError(403, "FORBIDDEN", "Hanya organizer yang dapat mengunggah media event")

    event = session.get(Event, event_id)
    if event is None:
        raise APIError(404, "EVENT_NOT_FOUND", f"Event '{event_id}' tidak ditemukan")

    from sqlalchemy import select
    from app.modules.organizers.models import Organizer

    organizer = session.scalar(
        select(Organizer).where(Organizer.owner_user_id == current_user.id)
    )
    if organizer is None or organizer.id != event.organizer_id:
        raise APIError(403, "FORBIDDEN", "Anda bukan pemilik event ini")

    raise APIError(
        501,
        "NOT_IMPLEMENTED",
        "Unggahan media belum tersedia. Fitur ini akan diaktifkan pada BE-009.",
    )
