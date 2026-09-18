"""Business logic for BE-002 Event APIs and BE-003 Match calculation.

Aligned to shared/API.md + shared/ARCHITECTURE.md:
  BE-API-004  GET  /api/events      — role-scoped list with filters
  BE-API-005  GET  /api/events/{id} — full detail with claim + organizer reliability
  BE-API-007  POST /api/events      — create event + inline venue + claim
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.modules.events.models import AccessibilityClaim, Event
from app.modules.events.schemas import (
    ClaimBody,
    ClaimInput,
    EventCreate,
    EventDetail,
    EventListItem,
    EventListResponse,
    MatchBreakdown,
    MatchResponse,
    OrganizerEmbed,
    VenueEmbed,
)
from app.modules.organizers.models import Organizer
from app.modules.users.models import NeedProfile
from app.modules.venues.models import Venue
from app.modules.verification.models import Verification


# ---------------------------------------------------------------------------
# Reliability helpers (provisional — full computation lives in BE-005)
# ---------------------------------------------------------------------------

def _organizer_embed(organizer: Organizer, session: Session) -> OrganizerEmbed:
    """
    Build OrganizerEmbed with provisional reliability score.

    P0 rule (ARCHITECTURE.md §reliability):
      - Map each of the seven verification answers to 1 / 0.5 / 0.
      - Average these values across the 20 most-recent verifications for that organizer.
      - Multiply by 100 and round → score 0–100.
      - sample_count = number of verifications in that window (not attributes).
      - No evidence → score:null, sample_count:0.
    """
    from app.modules.accessibility_requests.models import AccessibilityRequest

    # Correct join path: Verification → AccessibilityRequest → Event → Organizer
    rows = session.scalars(
        select(Verification)
        .join(
            AccessibilityRequest,
            Verification.request_id == AccessibilityRequest.id,
        )
        .join(Event, AccessibilityRequest.event_id == Event.id)
        .where(Event.organizer_id == organizer.id)
        .order_by(Verification.submitted_at.desc())
        .limit(20)
    ).all()

    sample_count = len(rows)
    if sample_count == 0:
        return OrganizerEmbed(
            id=organizer.id,
            name=organizer.name,
            reliability_score=None,
            sample_count=0,
        )

    attribute_keys = [
        "step_free_entrance",
        "elevator_or_ramp",
        "accessible_restroom",
        "accessible_seating",
        "rest_area",
        "parking_or_dropoff",
        "walking_distance",
    ]
    value_map = {"fulfilled": 1.0, "partially_fulfilled": 0.5, "not_fulfilled": 0.0}

    # Average per-verification (each verification contributes one average across its 7 keys)
    verification_averages: list[float] = []
    for v in rows:
        attrs: dict = v.attributes or {}
        values = [
            value_map[attrs[key]]
            for key in attribute_keys
            if attrs.get(key) in value_map
        ]
        if values:
            verification_averages.append(sum(values) / len(values))

    score = (
        round(100 * sum(verification_averages) / len(verification_averages))
        if verification_averages
        else None
    )
    return OrganizerEmbed(
        id=organizer.id,
        name=organizer.name,
        reliability_score=score,
        sample_count=sample_count,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require_organizer_by_user(user_id: str, session: Session) -> Organizer:
    org = session.scalar(
        select(Organizer).where(Organizer.owner_user_id == user_id)
    )
    if org is None:
        raise APIError(
            403,
            "NOT_AN_ORGANIZER",
            "Hanya organizer yang terdaftar yang dapat membuat event",
        )
    return org


def _build_venue_embed(venue: Venue) -> VenueEmbed:
    return VenueEmbed(
        id=venue.id,
        name=venue.name,
        city=venue.city,
        address=venue.address,
    )


def _build_detail(event: Event, session: Session) -> EventDetail:
    venue = session.get(Venue, event.venue_id)
    if venue is None:
        raise APIError(500, "DATA_INTEGRITY_ERROR", f"Venue untuk event '{event.id}' tidak ditemukan")
    claim = session.get(AccessibilityClaim, event.id)
    organizer = session.get(Organizer, event.organizer_id)
    if organizer is None:
        raise APIError(500, "DATA_INTEGRITY_ERROR", f"Organizer untuk event '{event.id}' tidak ditemukan")

    return EventDetail(
        id=event.id,
        title=event.title,
        description=event.description,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        status=event.status,  # type: ignore[arg-type]
        venue=_build_venue_embed(venue),
        organizer=_organizer_embed(organizer, session),
        claim=ClaimBody.model_validate(claim) if claim else None,
    )


def _build_list_item(event: Event, session: Session) -> EventListItem:
    venue = session.get(Venue, event.venue_id)
    if venue is None:
        raise APIError(500, "DATA_INTEGRITY_ERROR", f"Venue untuk event '{event.id}' tidak ditemukan")
    organizer = session.get(Organizer, event.organizer_id)
    if organizer is None:
        raise APIError(500, "DATA_INTEGRITY_ERROR", f"Organizer untuk event '{event.id}' tidak ditemukan")
    return EventListItem(
        id=event.id,
        title=event.title,
        starts_at=event.starts_at,
        status=event.status,  # type: ignore[arg-type]
        venue=VenueEmbed(
            id=venue.id,
            name=venue.name,
            city=venue.city,
            address=venue.address,
        ),
        organizer=_organizer_embed(organizer, session),
    )


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def create_event(payload: EventCreate, user_id: str, session: Session) -> EventDetail:
    """
    POST /api/events — BE-API-007.
    Creates a new Venue, Event, and AccessibilityClaim atomically.
    Owner is resolved from the JWT sub; body organizer_id is ignored.
    source must be 'organizer' (validated in schema).
    """
    organizer = _require_organizer_by_user(user_id, session)
    now = datetime.now(timezone.utc)

    # Derive status from timestamps
    status = "upcoming" if payload.starts_at > now else "completed"

    venue_id = str(uuid4())
    event_id = str(uuid4())

    venue = Venue(
        id=venue_id,
        name=payload.venue.name,
        city=payload.venue.city,
        address=payload.venue.address,
        source="organizer",
        checked_at=now,
    )
    session.add(venue)

    event = Event(
        id=event_id,
        organizer_id=organizer.id,
        venue_id=venue_id,
        title=payload.title,
        description=payload.description,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        status=status,
        published_at=now,
    )
    session.add(event)

    claim = AccessibilityClaim(
        event_id=event_id,
        step_free_entrance=payload.claim.step_free_entrance,
        elevator_or_ramp=payload.claim.elevator_or_ramp,
        accessible_restroom=payload.claim.accessible_restroom,
        accessible_seating=payload.claim.accessible_seating,
        rest_area=payload.claim.rest_area,
        parking_or_dropoff=payload.claim.parking_or_dropoff,
        walking_distance_m=payload.claim.walking_distance_m,
        source="organizer",   # always forced to 'organizer' for this endpoint
        checked_at=now,
    )
    session.add(claim)
    session.commit()
    session.refresh(event)

    return _build_detail(event, session)


def list_events(
    session: Session,
    *,
    user_id: str,
    user_role: str,
    status: str | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
    mine: bool = False,
) -> EventListResponse:
    """
    GET /api/events — BE-API-004.
    Either role; organizer may use mine=true to filter their own events.
    Attendee using mine=true → 403.
    Sort: starts_at ASC, then id ASC.
    """
    if mine and user_role != "organizer":
        raise APIError(403, "FORBIDDEN", "mine=true hanya tersedia untuk organizer")

    stmt = select(Event)

    if status is not None:
        stmt = stmt.where(Event.status == status)

    if mine:
        organizer = session.scalar(
            select(Organizer).where(Organizer.owner_user_id == user_id)
        )
        if organizer is None:
            # Organizer user with no organizer record → empty list
            return EventListResponse(items=[], total=0, limit=limit, offset=offset)
        stmt = stmt.where(Event.organizer_id == organizer.id)

    if q:
        term = f"%{q[:100]}%"
        stmt = stmt.where(Event.title.ilike(term))

    # Total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = session.scalar(count_stmt) or 0

    # Paginated rows
    rows = session.scalars(
        stmt.order_by(Event.starts_at.asc(), Event.id.asc())
        .limit(limit)
        .offset(offset)
    ).all()

    items = [_build_list_item(row, session) for row in rows]
    return EventListResponse(items=items, total=total, limit=limit, offset=offset)


def get_event(event_id: str, session: Session) -> EventDetail:
    """GET /api/events/{event_id} — BE-API-005."""
    event = session.get(Event, event_id)
    if event is None:
        raise APIError(404, "EVENT_NOT_FOUND", f"Event '{event_id}' tidak ditemukan")
    return _build_detail(event, session)


def calculate_match(user_id: str, event_id: str, session: Session) -> MatchResponse:
    profile = session.get(NeedProfile, user_id)
    if profile is None:
        raise APIError(
            409,
            "NEED_PROFILE_MISSING",
            "Harap isi profil kebutuhan aksesibilitas terlebih dahulu",
        )

    event = session.get(Event, event_id)
    if event is None:
        raise APIError(404, "EVENT_NOT_FOUND", "Event tidak ditemukan")

    claim = session.get(AccessibilityClaim, event_id)
    if claim is None:
        raise APIError(404, "CLAIM_NOT_FOUND", "Data aksesibilitas belum tersedia")

    facility_attrs = [
        "step_free_entrance",
        "elevator_or_ramp",
        "accessible_restroom",
        "accessible_seating",
        "rest_area",
        "parking_or_dropoff",
    ]

    breakdowns = []
    unknowns = []
    total_coeff = 0.0

    for attr in facility_attrs:
        is_required = getattr(profile, attr)
        coeff = 2.0 if is_required else 0.25

        claim_val = getattr(claim, attr)
        if claim_val is None:
            fulfillment = None
            unknowns.append(attr)
            label = "unknown"
        else:
            fulfillment = float(claim_val)
            if fulfillment == 1.0:
                label = "fulfilled"
            elif fulfillment == 0.5:
                label = "partially_fulfilled"
            else:
                label = "not_fulfilled"

        total_coeff += coeff
        breakdowns.append(
            MatchBreakdown(
                attribute=attr,
                required=is_required,
                weight=coeff,
                fulfillment=fulfillment,
                label=label,
            )
        )

    dist_req = profile.walking_distance
    if dist_req == "short":
        coeff = 2.0
    elif dist_req == "moderate":
        coeff = 1.0
    else:
        coeff = 0.25
    total_coeff += coeff

    claim_dist = claim.walking_distance_m
    if claim_dist is None:
        fulfillment = None
        unknowns.append("walking_distance")
        label = "unknown"
    else:
        if dist_req == "short":
            if claim_dist <= 200:
                fulfillment = 1.0
                label = "fulfilled"
            elif claim_dist <= 500:
                fulfillment = 0.5
                label = "partially_fulfilled"
            else:
                fulfillment = 0.0
                label = "not_fulfilled"
        elif dist_req == "moderate":
            if claim_dist <= 500:
                fulfillment = 1.0
                label = "fulfilled"
            elif claim_dist <= 1000:
                fulfillment = 0.5
                label = "partially_fulfilled"
            else:
                fulfillment = 0.0
                label = "not_fulfilled"
        else:
            fulfillment = 1.0
            label = "fulfilled"

    breakdowns.append(
        MatchBreakdown(
            attribute="walking_distance",
            required=True,
            weight=coeff,
            fulfillment=fulfillment,
            label=label,
        )
    )

    score_sum = 0.0
    for bd in breakdowns:
        if bd.fulfillment is not None:
            score_sum += (bd.weight / total_coeff) * bd.fulfillment

    final_score = round(100 * score_sum)

    summary = "Kecocokan dihitung berdasarkan kebutuhan Anda."
    if unknowns:
        summary = "Some required information is unknown; contact the organizer."

    return MatchResponse(
        event_id=event_id,
        score=final_score,
        weight_version="provisional-v1",
        breakdown=breakdowns,
        unknown_attributes=unknowns,
        summary=summary,
    )