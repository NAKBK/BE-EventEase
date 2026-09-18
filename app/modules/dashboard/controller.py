"""BE-011 / BE-API-019: GET /api/me/dashboard.

Router is mounted at prefix /api/me in main.py, alongside the needs endpoints.
"""

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, SessionDep
from app.core.errors import APIError
from app.modules.dashboard.schemas import AttendeeDashboardResponse
from app.modules.dashboard.service import get_attendee_dashboard

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=AttendeeDashboardResponse)
def get_dashboard(
    session: SessionDep,
    current_user: CurrentUser,
) -> AttendeeDashboardResponse:
    """
    BE-API-019: one-call summary for the attendee dashboard screen —
    pending request count, the active upcoming event (if any) with its
    match score, and recent request activity. Requires role=attendee.
    """
    if current_user.role != "attendee":
        raise APIError(403, "FORBIDDEN", "Hanya attendee yang memiliki dashboard ini")
    return get_attendee_dashboard(current_user.id, session)
