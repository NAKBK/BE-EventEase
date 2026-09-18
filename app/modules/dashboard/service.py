"""BE-011 / BE-API-019: attendee dashboard summary.

Pure composition over already-implemented reads (accessibility_requests,
events, the BE-API-006 match formula) — this module never computes a score
or maps a request/event shape on its own.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.accessibility_requests.models import AccessibilityRequest
from app.modules.accessibility_requests.schemas import RequestItem
from app.modules.accessibility_requests.service import map_request_response
from app.modules.dashboard.schemas import (
    ActiveEventSummary,
    AttendeeDashboardResponse,
    DashboardMatch,
)
from app.modules.events.models import Event
from app.modules.events.service import build_event_list_item, calculate_match

RECENT_REQUESTS_LIMIT = 5


def _find_active_event(user_id: str, session: Session) -> ActiveEventSummary | None:
    """
    Among the attendee's confirmed requests, the one whose event is still
    upcoming, soonest starts_at first. A confirmed request whose event has
    since completed is deliberately excluded — that one is waiting on
    verification, not on attendance.
    """
    row = session.execute(
        select(AccessibilityRequest, Event)
        .join(Event, AccessibilityRequest.event_id == Event.id)
        .where(
            AccessibilityRequest.attendee_id == user_id,
            AccessibilityRequest.status == "confirmed",
            Event.status == "upcoming",
        )
        .order_by(Event.starts_at.asc(), Event.id.asc())
        .limit(1)
    ).first()

    if row is None:
        return None

    request, event = row
    match = calculate_match(user_id, event.id, session)
    return ActiveEventSummary(
        request_id=request.id,
        event=build_event_list_item(event, session),
        match=DashboardMatch(
            score=match.score,
            weight_version=match.weight_version,
            unknown_attributes=match.unknown_attributes,
        ),
    )


def get_attendee_dashboard(user_id: str, session: Session) -> AttendeeDashboardResponse:
    pending_requests_count = (
        session.scalar(
            select(func.count())
            .select_from(AccessibilityRequest)
            .where(
                AccessibilityRequest.attendee_id == user_id,
                AccessibilityRequest.status == "pending",
            )
        )
        or 0
    )

    active_event = _find_active_event(user_id, session)

    recent_rows = session.execute(
        select(AccessibilityRequest, Event)
        .join(Event, AccessibilityRequest.event_id == Event.id)
        .where(AccessibilityRequest.attendee_id == user_id)
        .order_by(AccessibilityRequest.created_at.desc())
        .limit(RECENT_REQUESTS_LIMIT)
    ).all()
    recent_requests = [
        RequestItem(**{**map_request_response(req).model_dump(), "event_title": event.title})
        for req, event in recent_rows
    ]

    return AttendeeDashboardResponse(
        pending_requests_count=pending_requests_count,
        active_event=active_event,
        recent_requests=recent_requests,
    )
