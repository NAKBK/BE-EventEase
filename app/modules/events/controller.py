"""BE-002: /api/events endpoints.

Aligned to shared/API.md:
  BE-API-004  GET  /api/events             — role-scoped list with filters
  BE-API-005  GET  /api/events/{event_id}  — full event detail
  BE-API-007  POST /api/events             — organizer creates event + claim
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, SessionDep
from app.core.errors import APIError
from app.modules.events.schemas import EventCreate, EventDetail, EventListResponse
from app.modules.events.service import create_event, get_event, list_events


router = APIRouter(tags=["events"])


@router.get("", response_model=EventListResponse)
def get_events(
    session: SessionDep,
    current_user: CurrentUser,
    status: Annotated[
        Literal["upcoming", "completed"] | None,
        Query(description="Filter by event status"),
    ] = None,
    q: Annotated[
        str | None,
        Query(max_length=100, description="Search by title (case-insensitive)"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=50, description="Page size")] = 20,
    offset: Annotated[int, Query(ge=0, description="Page offset")] = 0,
    mine: Annotated[
        bool,
        Query(description="Organizer only: filter to own events"),
    ] = False,
) -> EventListResponse:
    """
    BE-API-004: List events.
    Requires auth (either role). Attendee using mine=true → 403.
    """
    return list_events(
        session,
        user_id=current_user.id,
        user_role=current_user.role,
        status=status,
        q=q,
        limit=limit,
        offset=offset,
        mine=mine,
    )


@router.get("/{event_id}", response_model=EventDetail)
def get_event_by_id(
    event_id: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> EventDetail:
    """
    BE-API-005: Get full event detail.
    Requires auth (either role).
    """
    return get_event(event_id, session)


@router.post("", response_model=EventDetail, status_code=201)
def post_event(
    payload: EventCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> EventDetail:
    """
    BE-API-007: Create a new event with inline venue and accessibility claim.
    Requires role=organizer. BE sets owner from token — body organizer_id ignored.
    claim.source must be 'organizer'.
    """
    if current_user.role != "organizer":
        raise APIError(403, "FORBIDDEN", "Hanya organizer yang dapat membuat event")
    return create_event(payload, current_user.id, session)
