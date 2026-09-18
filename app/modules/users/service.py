"""Business logic for BE-002 Need Profile APIs.

Aligned to shared/API.md:
  BE-API-002  GET /api/me/needs  — read profile (null if not yet saved)
  BE-API-003  PUT /api/me/needs  — replace all seven values atomically
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.modules.users.models import NeedProfile
from app.modules.users.schemas import NeedProfileBody, NeedProfileResponse, NeedProfileUpsert


def get_need_profile(user_id: str, session: Session) -> NeedProfileResponse:
    """
    GET /api/me/needs — BE-API-002.
    Returns the seven-key profile and updated_at.
    If no profile exists yet, returns profile:null, updated_at:null
    (API.md: 'If no profile exists: profile:null, updated_at:null before first save').
    """
    profile = session.get(NeedProfile, user_id)
    if profile is None:
        return NeedProfileResponse(profile=None, updated_at=None)

    return NeedProfileResponse(
        profile=NeedProfileBody.model_validate(profile),
        updated_at=profile.updated_at,
    )


def upsert_need_profile(
    user_id: str,
    payload: NeedProfileUpsert,
    session: Session,
) -> NeedProfileResponse:
    """
    PUT /api/me/needs — BE-API-003.
    Atomically replaces all seven profile values.
    Only touches the authenticated attendee's own profile.
    Returns the same response shape as GET.
    """
    profile = session.get(NeedProfile, user_id)
    now = datetime.now(timezone.utc)

    if profile is None:
        profile = NeedProfile(user_id=user_id)
        session.add(profile)

    profile.step_free_entrance = payload.step_free_entrance
    profile.elevator_or_ramp = payload.elevator_or_ramp
    profile.accessible_restroom = payload.accessible_restroom
    profile.accessible_seating = payload.accessible_seating
    profile.rest_area = payload.rest_area
    profile.parking_or_dropoff = payload.parking_or_dropoff
    profile.walking_distance = payload.walking_distance
    profile.updated_at = now

    session.commit()
    session.refresh(profile)

    return NeedProfileResponse(
        profile=NeedProfileBody.model_validate(profile),
        updated_at=profile.updated_at,
    )
