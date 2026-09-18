"""BE-002: /api/me/needs endpoints.

Aligned to shared/API.md:
  BE-API-002  GET /api/me/needs  — read saved need profile
  BE-API-003  PUT /api/me/needs  — replace all seven values atomically

Router is mounted at prefix /api/me in main.py.
"""

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, SessionDep
from app.core.errors import APIError
from app.modules.users.models import User
from app.modules.users.schemas import NeedProfileResponse, NeedProfileUpsert
from app.modules.users.service import get_need_profile, upsert_need_profile


router = APIRouter(tags=["needs"])


def _require_attendee(current_user: User) -> None:
    if current_user.role != "attendee":
        raise APIError(403, "FORBIDDEN", "Hanya attendee yang memiliki profil kebutuhan")


@router.get("/needs", response_model=NeedProfileResponse)
def read_need_profile(
    session: SessionDep,
    current_user: CurrentUser,
) -> NeedProfileResponse:
    """
    BE-API-002: GET /api/me/needs
    Returns the authenticated user's need profile.
    Returns {profile: null, updated_at: null} if no profile saved yet — never 404.
    Auth: attendee bearer only (shared/API.md BE-API-002).
    """
    _require_attendee(current_user)
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
    Auth: attendee bearer only (shared/API.md BE-API-003).
    """
    _require_attendee(current_user)
    return upsert_need_profile(current_user.id, payload, session)