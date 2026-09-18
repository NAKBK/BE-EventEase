from fastapi import APIRouter

from app.core.dependencies import CurrentUser, SessionDep
from app.modules.organizers.schemas import OrganizerProfileResponse
from app.modules.organizers.service import get_organizer_profile

router = APIRouter(tags=["organizers"])


@router.get("/{organizer_id}", response_model=OrganizerProfileResponse)
def get_organizer(
    organizer_id: str, session: SessionDep, _user: CurrentUser
) -> OrganizerProfileResponse:
    return get_organizer_profile(organizer_id, session)
