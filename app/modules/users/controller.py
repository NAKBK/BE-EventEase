"""BE-002: /api/me/needs endpoints.

Aligned to shared/API.md:
  BE-API-002  GET /api/me/needs  — read saved need profile
  BE-API-003  PUT /api/me/needs  — replace all seven values atomically

Router is mounted at prefix /api/me in main.py.
"""

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, SessionDep
from app.modules.users.schemas import NeedProfileResponse, NeedProfileUpsert
from app.modules.users.service import get_need_profile, upsert_need_profile


router = APIRouter(tags=["needs"])


@router.get("/needs", response_model=NeedProfileResponse)
def read_need_profile(
    session: SessionDep,
    current_user: CurrentUser,
) -> NeedProfileResponse:
    """
    BE-API-002: GET /api/me/needs
    Returns the authenticated user's need profile.
    Returns {profile: null, updated_at: null} if no profile saved yet — never 404.
    Auth: either role bearer.
    """
    return get_need_profile(current_user.id, session)


@router.put("/needs", response_model=NeedProfileResponse)
def write_need_profile(
    payload: NeedProfileUpsert,
    session: SessionDep,
    current_user: CurrentUser,
) -> NeedProfileResponse:
    """
    BE-API-003: PUT /api/me/needs
    Atomically replaces all seven profile values.
    Returns the same shape as GET with updated timestamp.
    Auth: either role bearer (API.md does not restrict to attendee only).
    """
    return upsert_need_profile(current_user.id, payload, session)