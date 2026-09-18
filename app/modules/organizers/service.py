from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.modules.accessibility_requests.models import AccessibilityRequest
from app.modules.events.models import Event
from app.modules.organizers.models import Organizer
from app.modules.organizers.schemas import OrganizerProfileResponse, OrganizerReliability
from app.modules.verification.models import Verification


ATTRIBUTE_VALUES = {
    "fulfilled": 1.0,
    "partially_fulfilled": 0.5,
    "not_fulfilled": 0.0,
}
RELIABILITY_WINDOW_SIZE = 20


def get_organizer_reliability(
    organizer_id: str, session: Session
) -> OrganizerReliability:
    """Compute reliability from the 20 most recent completed verifications."""
    verifications = session.scalars(
        select(Verification)
        .join(AccessibilityRequest, Verification.request_id == AccessibilityRequest.id)
        .join(Event, AccessibilityRequest.event_id == Event.id)
        .where(Event.organizer_id == organizer_id)
        .order_by(Verification.submitted_at.desc())
        .limit(RELIABILITY_WINDOW_SIZE)
    ).all()

    if not verifications:
        return OrganizerReliability(
            score=None,
            sample_count=0,
            updated_at=None,
        )

    values = [
        ATTRIBUTE_VALUES[value]
        for verification in verifications
        for value in verification.attributes.values()
        if value in ATTRIBUTE_VALUES
    ]
    # Every persisted verification contains all seven values; retain a safe
    # fallback for legacy/incomplete rows instead of reporting a false score.
    score = round(100 * sum(values) / len(values)) if values else None
    return OrganizerReliability(
        score=score,
        sample_count=len(verifications),
        updated_at=verifications[0].submitted_at,
    )


def get_organizer_profile(organizer_id: str, session: Session) -> OrganizerProfileResponse:
    organizer = session.get(Organizer, organizer_id)
    if organizer is None:
        raise APIError(404, "ORGANIZER_NOT_FOUND", "Organizer tidak ditemukan")
    return OrganizerProfileResponse(
        id=organizer.id,
        name=organizer.name,
        reliability=get_organizer_reliability(organizer.id, session),
    )
