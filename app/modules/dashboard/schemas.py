"""BE-011 / BE-API-019: GET /api/me/dashboard response shapes.

Composes existing shapes only (EventListItem, RequestItem) plus one small
match summary — this module never redefines an event, request, or claim
shape of its own.
"""

from pydantic import BaseModel

from app.modules.accessibility_requests.schemas import RequestItem
from app.modules.events.schemas import EventListItem


class DashboardMatch(BaseModel):
    """Trimmed match summary — score/version/unknowns only.

    Full per-attribute breakdown is available via GET /events/{id}/match
    (BE-API-006); this dashboard summary intentionally doesn't repeat it.
    """

    score: int
    weight_version: str
    unknown_attributes: list[str]


class ActiveEventSummary(BaseModel):
    request_id: str
    event: EventListItem
    match: DashboardMatch


class AttendeeDashboardResponse(BaseModel):
    pending_requests_count: int
    active_event: ActiveEventSummary | None
    recent_requests: list[RequestItem]
