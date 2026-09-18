"""BE-002/003/010: /api/events endpoints.

Aligned to shared/API.md:
  BE-API-004  GET  /api/events                    — role-scoped list with filters
  BE-API-005  GET  /api/events/{event_id}          — full event detail
  BE-API-006  GET  /api/events/{event_id}/match    — personalized match score
  BE-API-007  POST /api/events                    — organizer creates event + claim
  BE-API-018  GET  /api/events (extended)          — attribute/date filters, sort=match_score

Router is mounted at prefix /api/events in main.py.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request

from app.core.dependencies import CurrentUser, SessionDep
from app.core.errors import APIError
from app.modules.events.schemas import (
    EventCreate,
    EventDetail,
    EventListResponse,
    MatchResponse,
)
from app.modules.events.service import FACILITY_ATTRS, calculate_match, create_event, get_event, list_events


router = APIRouter(tags=["events"])

FacilityScoreParam = Annotated[
    Literal[0, 0.5, 1] | None,
    Query(description="Require this exact claim value for the attribute"),
]

_ALLOWED_LIST_QUERY_KEYS = {
    "status",
    "q",
    "limit",
    "offset",
    "mine",
    "date_from",
    "date_to",
    "sort",
    *FACILITY_ATTRS,
}


@router.get("", response_model=EventListResponse)
def get_events(
    request: Request,
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
    date_from: Annotated[
        date | None, Query(description="Inclusive lower bound on starts_at (ISO date)")
    ] = None,
    date_to: Annotated[
        date | None, Query(description="Inclusive upper bound on starts_at (ISO date)")
    ] = None,
    sort: Annotated[
        Literal["starts_at", "match_score"] | None,
        Query(description="Sort order; match_score requires attendee bearer + saved profile"),
    ] = "starts_at",
    step_free_entrance: FacilityScoreParam = None,
    elevator_or_ramp: FacilityScoreParam = None,
    accessible_restroom: FacilityScoreParam = None,
    accessible_seating: FacilityScoreParam = None,
    rest_area: FacilityScoreParam = None,
    parking_or_dropoff: FacilityScoreParam = None,
) -> EventListResponse:
    """
    BE-API-004 / BE-API-018: List events, with optional attribute/date
    filters and sort=match_score (BE-010).
    Requires auth (either role). Attendee using mine=true → 403.
    """
    unknown_keys = set(request.query_params.keys()) - _ALLOWED_LIST_QUERY_KEYS
    if unknown_keys:
        raise APIError(
            422,
            "VALIDATION_ERROR",
            f"Query parameter tidak dikenal: {', '.join(sorted(unknown_keys))}",
        )

    facility_values = {
        "step_free_entrance": step_free_entrance,
        "elevator_or_ramp": elevator_or_ramp,
        "accessible_restroom": accessible_restroom,
        "accessible_seating": accessible_seating,
        "rest_area": rest_area,
        "parking_or_dropoff": parking_or_dropoff,
    }
    facility_filters = {
        attr: Decimal(str(value))
        for attr, value in facility_values.items()
        if value is not None
    }

    return list_events(
        session,
        user_id=current_user.id,
        user_role=current_user.role,
        status=status,
        q=q,
        limit=limit,
        offset=offset,
        mine=mine,
        facility_filters=facility_filters or None,
        date_from=date_from,
        date_to=date_to,
        sort=sort or "starts_at",
    )


@router.get("/{event_id}/match", response_model=MatchResponse)
def get_event_match(
    event_id: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> MatchResponse:
    """
    BE-API-006: Personalized match score for an attendee's saved needs vs event claim.
    Requires role=attendee. Returns 403 for organizer.
    Returns 409 NEED_PROFILE_MISSING if attendee has no saved profile.
    """
    if current_user.role != "attendee":
        raise APIError(403, "FORBIDDEN", "Hanya attendee yang dapat mengecek kecocokan event")
    return calculate_match(current_user.id, event_id, session)


@router.get("/{event_id}", response_model=EventDetail)
def get_event_by_id(
    event_id: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> EventDetail:
    """
    BE-API-005: Get full event detail including venue, organizer, claim, and media.
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
    """
    if current_user.role != "organizer":
        raise APIError(403, "FORBIDDEN", "Hanya organizer yang dapat membuat event")
    return create_event(payload, current_user.id, session)
