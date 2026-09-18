"""Business logic for BE-002 Event APIs, BE-003 Match calculation, and
BE-010 advanced search.

Aligned to shared/API.md + shared/ARCHITECTURE.md:
  BE-API-004  GET  /api/events      — role-scoped list with filters
  BE-API-005  GET  /api/events/{id} — full detail with claim + organizer reliability
  BE-API-007  POST /api/events      — create event + inline venue + claim
  BE-API-018  GET  /api/events (extended) — attribute/date filters, sort=match_score
"""

from datetime import date, datetime, time, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.modules.events.models import AccessibilityClaim, Event, EventMedia
from app.modules.events.schemas import (
    ClaimBody,
    ClaimInput,
    EventCreate,
    EventDetail,
    EventListItem,
    EventListResponse,
    MatchBreakdown,
    MatchResponse,
    MediaItem,
    OrganizerEmbed,
    VenueEmbed,
)
from app.modules.organizers.models import Organizer
from app.modules.organizers.service import get_organizer_reliability
from app.modules.users.models import NeedProfile
from app.modules.venues.models import Venue


FACILITY_ATTRS = (
    "step_free_entrance",
    "elevator_or_ramp",
    "accessible_restroom",
    "accessible_seating",
    "rest_area",
    "parking_or_dropoff",
)


# ---------------------------------------------------------------------------
# Reliability helpers
# ---------------------------------------------------------------------------

def _organizer_embed(organizer: Organizer, session: Session) -> OrganizerEmbed:
    """Build OrganizerEmbed, reusing the single reliability computation
    (app.modules.organizers.service.get_organizer_reliability) shared with
    the organizer profile endpoint and the verification submission response.
    """
    reliability = get_organizer_reliability(organizer.id, session)
    return OrganizerEmbed(
        id=organizer.id,
        name=organizer.name,
        reliability_score=reliability.score,
        sample_count=reliability.sample_count,
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
    # Venue model stores latitude/longitude; API contract uses lat/lng.
    return VenueEmbed(
        id=venue.id,
        name=venue.name,
        city=venue.city,
        address=venue.address,
        lat=venue.latitude,
        lng=venue.longitude,
    )


def _build_detail(event: Event, session: Session) -> EventDetail:
    venue = session.get(Venue, event.venue_id)
    if venue is None:
        raise APIError(500, "DATA_INTEGRITY_ERROR", f"Venue untuk event '{event.id}' tidak ditemukan")
    claim = session.get(AccessibilityClaim, event.id)
    organizer = session.get(Organizer, event.organizer_id)
    if organizer is None:
        raise APIError(500, "DATA_INTEGRITY_ERROR", f"Organizer untuk event '{event.id}' tidak ditemukan")

    media_rows = session.scalars(
        select(EventMedia)
        .where(EventMedia.event_id == event.id)
        .order_by(EventMedia.uploaded_at.asc())
    ).all()

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
        media=[MediaItem.model_validate(m) for m in media_rows],
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
        venue=_build_venue_embed(venue),
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
        latitude=payload.venue.lat,    # VenueCreate uses lat/lng; model uses latitude/longitude
        longitude=payload.venue.lng,
        source="organizer",
        checked_at=now,
    )
    session.add(venue)
    session.flush()  # write venue to DB so event FK resolves

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
    session.flush()  # write event to DB so accessibility_claims FK resolves

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
    facility_filters: dict[str, Decimal] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort: str = "starts_at",
) -> EventListResponse:
    """
    GET /api/events — BE-API-004, extended by BE-API-018 (BE-010).
    Either role; organizer may use mine=true to filter their own events.
    Attendee using mine=true → 403.

    BE-010 additions:
      - facility_filters: exact-match against stored Claim values (0/0.5/1).
        A null claim never matches, per API.md's explicit rule.
      - date_from/date_to: inclusive day-range on starts_at (UTC day bounds).
      - sort="starts_at" (default, DB-level) or "match_score" (attendee-only,
        requires a saved NeedProfile; computed in Python via _compute_match
        since a score cannot be expressed as a SQL column).
    """
    if mine and user_role != "organizer":
        raise APIError(403, "FORBIDDEN", "mine=true hanya tersedia untuk organizer")

    if sort == "match_score" and user_role != "attendee":
        raise APIError(403, "FORBIDDEN", "sort=match_score hanya tersedia untuk attendee")

    if date_from is not None and date_to is not None and date_from > date_to:
        raise APIError(422, "VALIDATION_ERROR", "date_from harus sebelum atau sama dengan date_to")

    profile: NeedProfile | None = None
    if sort == "match_score":
        profile = session.get(NeedProfile, user_id)
        if profile is None:
            raise APIError(
                409,
                "NEED_PROFILE_MISSING",
                "Harap isi profil kebutuhan aksesibilitas terlebih dahulu",
            )

    stmt = select(Event)

    if facility_filters:
        stmt = stmt.join(AccessibilityClaim, AccessibilityClaim.event_id == Event.id)
        for attr, value in facility_filters.items():
            stmt = stmt.where(getattr(AccessibilityClaim, attr) == value)

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

    if date_from is not None:
        stmt = stmt.where(
            Event.starts_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        )
    if date_to is not None:
        stmt = stmt.where(
            Event.starts_at <= datetime.combine(date_to, time.max, tzinfo=timezone.utc)
        )

    if sort == "match_score":
        # Score isn't a SQL column: fetch every filtered row first (small
        # demo dataset), rank in Python, then slice for pagination.
        assert profile is not None  # guaranteed by the guard clause above
        all_rows = session.scalars(
            stmt.order_by(Event.starts_at.asc(), Event.id.asc())
        ).all()
        total = len(all_rows)

        scored: list[tuple[int, Event]] = []
        for event in all_rows:
            claim = session.get(AccessibilityClaim, event.id)
            score, *_ = _compute_match(profile, claim)
            scored.append((score, event))

        scored.sort(key=lambda pair: (-pair[0], pair[1].starts_at, pair[1].id))
        page = scored[offset : offset + limit]
        items = [_build_list_item(event, session) for _, event in page]
    else:
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = session.scalar(count_stmt) or 0

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


def _compute_match(
    profile: NeedProfile, claim: AccessibilityClaim | None
) -> tuple[int, list[MatchBreakdown], list[str], str]:
    """
    Pure scoring function shared by BE-API-006 (GET .../match) and BE-API-018
    (sort=match_score). Do not duplicate this logic elsewhere — BE-API-018's
    contract explicitly requires reusing this exact formula, not a separate
    calculation, so the two endpoints can never silently drift apart.

    claim=None is treated as if every attribute were unknown (score 0 for
    the numerator, weight still counted in the denominator) rather than
    raising — list-sorting must never 500 on a data-integrity edge case
    that a single-event lookup would reject outright.
    """
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

        claim_val = getattr(claim, attr) if claim is not None else None
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

    claim_dist = claim.walking_distance_m if claim is not None else None
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

    return final_score, breakdowns, unknowns, summary


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

    score, breakdown, unknowns, summary = _compute_match(profile, claim)

    return MatchResponse(
        event_id=event_id,
        score=score,
        weight_version="provisional-v1",
        breakdown=breakdown,
        unknown_attributes=unknowns,
        summary=summary,
    )