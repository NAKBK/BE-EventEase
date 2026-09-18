import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.errors import APIError
from app.modules.accessibility_requests.models import AccessibilityRequest
from app.modules.accessibility_requests.schemas import (
    AttendeeConfirmSubmit,
    NeedSnapshot,
    OrganizerResponseDetails,
    OrganizerResponseSubmit,
    RequestCreate,
    RequestItem,
    RequestResponse,
)
from app.modules.events.models import Event
from app.modules.organizers.models import Organizer
from app.modules.users.models import NeedProfile, User


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def map_request_response(req: AccessibilityRequest) -> RequestResponse:
    resp = None
    if req.response_decision is not None:
        resp = OrganizerResponseDetails(
            decision=req.response_decision,
            note=req.response_note,
            responded_at=req.responded_at,
        )

    return RequestResponse(
        id=req.id,
        event_id=req.event_id,
        attendee_id=req.attendee_id,
        status=req.status,
        needs_snapshot=NeedSnapshot(**req.needs_snapshot),
        arrival_estimate=req.arrival_estimate,
        note=req.note,
        response=resp,
        created_at=req.created_at,
        confirmed_at=req.confirmed_at,
    )


def create_request(
    attendee_id: str, event_id: str, payload: RequestCreate, session: Session
) -> RequestResponse:
    event = session.get(Event, event_id)
    if not event:
        raise APIError(404, "EVENT_NOT_FOUND", "Event tidak ditemukan")
    if event.status != "upcoming":
        raise APIError(409, "EVENT_NOT_UPCOMING", "Event sudah selesai")

    profile = session.get(NeedProfile, attendee_id)
    if not profile:
        raise APIError(409, "NEED_PROFILE_MISSING", "Profil kebutuhan belum diatur")

    existing_active = session.scalars(
        select(AccessibilityRequest).where(
            AccessibilityRequest.event_id == event_id,
            AccessibilityRequest.attendee_id == attendee_id,
            AccessibilityRequest.status.in_(("pending", "responded", "confirmed")),
        )
    ).first()
    if existing_active:
        raise APIError(409, "ACTIVE_REQUEST_EXISTS", "Anda sudah memiliki request aktif untuk event ini")

    snapshot = {
        "step_free_entrance": profile.step_free_entrance,
        "elevator_or_ramp": profile.elevator_or_ramp,
        "accessible_restroom": profile.accessible_restroom,
        "accessible_seating": profile.accessible_seating,
        "rest_area": profile.rest_area,
        "parking_or_dropoff": profile.parking_or_dropoff,
        "walking_distance": profile.walking_distance,
    }

    new_req = AccessibilityRequest(
        id=str(uuid.uuid4()),
        event_id=event_id,
        attendee_id=attendee_id,
        needs_snapshot=snapshot,
        arrival_estimate=payload.arrival_estimate,
        note=payload.note,
        status="pending",
    )
    session.add(new_req)
    session.commit()
    return map_request_response(new_req)


def list_requests(
    user: User, status: str | None, limit: int, offset: int, session: Session
) -> dict:
    query = select(AccessibilityRequest, Event).join(
        Event, AccessibilityRequest.event_id == Event.id
    )

    if user.role == "attendee":
        query = query.where(AccessibilityRequest.attendee_id == user.id)
    else:
        # Events reference the organizer profile id; bearer users own that
        # profile through Organizer.owner_user_id.
        query = query.join(Organizer, Event.organizer_id == Organizer.id).where(
            Organizer.owner_user_id == user.id
        )

    if status:
        query = query.where(AccessibilityRequest.status == status)

    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0

    query = query.order_by(AccessibilityRequest.created_at.desc()).limit(limit).offset(offset)
    results = session.execute(query).all()

    items = []
    for req, evt in results:
        base = map_request_response(req).model_dump()
        base["event_title"] = evt.title
        items.append(RequestItem(**base))

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def respond_to_request(
    organizer_user_id: str,
    request_id: str,
    payload: OrganizerResponseSubmit,
    session: Session,
) -> RequestResponse:
    req = session.get(AccessibilityRequest, request_id)
    if not req:
        raise APIError(404, "REQUEST_NOT_FOUND", "Request tidak ditemukan")

    event = session.get(Event, req.event_id)
    organizer = session.get(Organizer, event.organizer_id) if event else None
    if not event or organizer is None or organizer.owner_user_id != organizer_user_id:
        raise APIError(403, "FORBIDDEN", "Anda bukan pemilik event ini")

    if req.status != "pending":
        raise APIError(409, "INVALID_REQUEST_STATE", "Hanya request pending yang dapat direspons")

    req.response_decision = payload.decision
    req.response_note = payload.note
    req.responded_at = utcnow()
    req.status = "closed" if payload.decision == "cannot_fulfill" else "responded"

    session.commit()
    return map_request_response(req)


def confirm_response(
    attendee_id: str, request_id: str, payload: AttendeeConfirmSubmit, session: Session
) -> RequestResponse:
    req = session.get(AccessibilityRequest, request_id)
    if not req:
        raise APIError(404, "REQUEST_NOT_FOUND", "Request tidak ditemukan")

    if req.attendee_id != attendee_id:
        raise APIError(403, "FORBIDDEN", "Anda bukan pemilik request ini")

    if req.status != "responded":
        raise APIError(409, "INVALID_REQUEST_STATE", "Hanya request responded yang dapat dikonfirmasi")

    if payload.accepted:
        req.status = "confirmed"
        req.confirmed_at = utcnow()
    else:
        req.status = "closed"

    session.commit()
    return map_request_response(req)
