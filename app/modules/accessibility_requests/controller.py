from typing import Literal

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, SessionDep
from app.core.errors import APIError
from app.modules.accessibility_requests import service
from app.modules.accessibility_requests.schemas import (
    AttendeeConfirmSubmit,
    OrganizerResponseSubmit,
    RequestCreate,
    RequestResponse,
)

router = APIRouter(tags=["requests"])


@router.post("/events/{event_id}/requests", response_model=RequestResponse, status_code=201)
def submit_request(
    event_id: str, payload: RequestCreate, session: SessionDep, user: CurrentUser
) -> RequestResponse:
    if user.role != "attendee":
        raise APIError(403, "FORBIDDEN", "Hanya attendee yang dapat membuat request")
    return service.create_request(user.id, event_id, payload, session)


@router.get("/requests")
def list_my_requests(
    session: SessionDep,
    user: CurrentUser,
    status: Literal["pending", "responded", "confirmed", "closed", "verified"] | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> dict:
    return service.list_requests(user, status, limit, offset, session)


@router.post("/requests/{request_id}/response", response_model=RequestResponse)
def respond_request(
    request_id: str,
    payload: OrganizerResponseSubmit,
    session: SessionDep,
    user: CurrentUser,
) -> RequestResponse:
    if user.role != "organizer":
        raise APIError(403, "FORBIDDEN", "Hanya organizer yang dapat merespons request")
    return service.respond_to_request(user.id, request_id, payload, session)


@router.post("/requests/{request_id}/confirm", response_model=RequestResponse)
def confirm_response(
    request_id: str,
    payload: AttendeeConfirmSubmit,
    session: SessionDep,
    user: CurrentUser,
) -> RequestResponse:
    if user.role != "attendee":
        raise APIError(403, "FORBIDDEN", "Hanya attendee yang dapat mengonfirmasi request")
    return service.confirm_response(user.id, request_id, payload, session)
