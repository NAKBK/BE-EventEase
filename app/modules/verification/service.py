from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.errors import APIError
from app.modules.accessibility_requests.models import AccessibilityRequest
from app.modules.events.models import Event
from app.modules.organizers.service import get_organizer_reliability
from app.modules.verification.models import Verification
from app.modules.verification.schemas import VerificationCreate, VerificationResponse


def submit_verification(
    attendee_id: str,
    request_id: str,
    payload: VerificationCreate,
    session: Session,
) -> VerificationResponse:
    request = session.get(AccessibilityRequest, request_id)
    if request is None:
        raise APIError(404, "REQUEST_NOT_FOUND", "Request tidak ditemukan")
    if request.attendee_id != attendee_id:
        raise APIError(403, "FORBIDDEN", "Anda bukan pemilik request ini")

    existing_verification = session.scalar(
        select(Verification).where(Verification.request_id == request_id)
    )
    if existing_verification is not None:
        raise APIError(409, "ALREADY_VERIFIED", "Request ini sudah diverifikasi")

    event = session.get(Event, request.event_id)
    if event is None:
        raise APIError(500, "DATA_INTEGRITY_ERROR", "Event untuk request tidak ditemukan")
    event_ends_at = event.ends_at
    # SQLite returns timezone-aware columns as naive datetimes. Treat those
    # stored UTC values consistently with PostgreSQL's aware values.
    if event_ends_at.tzinfo is None:
        event_ends_at = event_ends_at.replace(tzinfo=timezone.utc)
    if event.status != "completed" or event_ends_at > datetime.now(timezone.utc):
        raise APIError(409, "EVENT_NOT_COMPLETED", "Event belum selesai")
    if request.status != "confirmed":
        raise APIError(409, "INVALID_REQUEST_STATE", "Hanya request confirmed yang dapat diverifikasi")

    verification = Verification(
        id=str(uuid4()),
        request_id=request.id,
        attendee_id=attendee_id,
        attributes=payload.attributes.model_dump(),
    )
    session.add(verification)
    request.status = "verified"
    session.commit()
    session.refresh(verification)

    return VerificationResponse(
        id=verification.id,
        request_id=request.id,
        status="verified",
        submitted_at=verification.submitted_at,
        organizer_reliability=get_organizer_reliability(event.organizer_id, session),
    )
