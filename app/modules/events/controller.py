from fastapi import APIRouter

from app.core.dependencies import CurrentUser, SessionDep
from app.core.errors import APIError
from app.modules.events import service
from app.modules.events.schemas import MatchResponse

router = APIRouter(tags=["events"])


@router.get("/events/{event_id}/match", response_model=MatchResponse)
def get_event_match(
    event_id: str, session: SessionDep, user: CurrentUser
) -> MatchResponse:
    if user.role != "attendee":
        raise APIError(403, "FORBIDDEN", "Hanya attendee yang dapat mengecek kecocokan")
    return service.calculate_match(user.id, event_id, session)
