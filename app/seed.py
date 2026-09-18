"""Idempotent, clearly labeled demo data for BE-001."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.accessibility_requests.models import AccessibilityRequest
from app.modules.events.models import AccessibilityClaim, Event
from app.modules.organizers.models import Organizer
from app.modules.users.models import NeedProfile, User
from app.modules.venues.models import Venue


DEMO_NEEDS = {
    "step_free_entrance": True,
    "elevator_or_ramp": True,
    "accessible_restroom": True,
    "accessible_seating": False,
    "rest_area": False,
    "parking_or_dropoff": True,
    "walking_distance": "short",
}


def seed_demo_data(session: Session) -> None:
    """Insert missing fixtures only; never overwrite a running demo's state."""
    now = datetime.now(timezone.utc)
    if session.get(User, "u-att-1") is None:
        session.add(User(id="u-att-1", display_name="Demo Attendee", role="attendee"))
    if session.get(User, "u-org-1") is None:
        session.add(User(id="u-org-1", display_name="Demo Organizer", role="organizer"))
    session.flush()

    if session.get(NeedProfile, "u-att-1") is None:
        session.add(NeedProfile(user_id="u-att-1", **DEMO_NEEDS, updated_at=now))
    if session.get(Organizer, "org-1") is None:
        session.add(
            Organizer(id="org-1", owner_user_id="u-org-1", name="Demo Organizer")
        )
    if session.get(Venue, "v-demo-1") is None:
        session.add(
            Venue(
                id="v-demo-1",
                name="Venue Demo Jakarta Pusat",
                city="Jakarta",
                address="Jakarta Pusat (lokasi fiktif untuk demo)",
                source="demo",
                checked_at=now,
            )
        )
    if session.get(Venue, "v-demo-2") is None:
        session.add(
            Venue(
                id="v-demo-2",
                name="Venue Demo Jakarta Selatan",
                city="Jakarta",
                address="Jakarta Selatan (lokasi fiktif untuk demo)",
                source="demo",
                checked_at=now,
            )
        )
    session.flush()

    upcoming_start = now + timedelta(days=3)
    past_start = now - timedelta(days=2)
    if session.get(Event, "evt-upcoming-1") is None:
        session.add(
            Event(
                id="evt-upcoming-1",
                organizer_id="org-1",
                venue_id="v-demo-1",
                title="Festival Akses Demo",
                description="Event fiktif untuk demonstrasi EventEase.",
                starts_at=upcoming_start,
                ends_at=upcoming_start + timedelta(hours=8),
                status="upcoming",
                published_at=now,
            )
        )
    if session.get(Event, "evt-past-1") is None:
        session.add(
            Event(
                id="evt-past-1",
                organizer_id="org-1",
                venue_id="v-demo-2",
                title="Seminar Akses Demo",
                description="Event lampau fiktif untuk alur verifikasi.",
                starts_at=past_start,
                ends_at=past_start + timedelta(hours=4),
                status="completed",
                published_at=past_start - timedelta(days=7),
            )
        )
    session.flush()

    if session.get(AccessibilityClaim, "evt-upcoming-1") is None:
        session.add(
            AccessibilityClaim(
                event_id="evt-upcoming-1",
                step_free_entrance=Decimal("1.0"),
                elevator_or_ramp=Decimal("0.5"),
                accessible_restroom=None,
                accessible_seating=Decimal("1.0"),
                rest_area=Decimal("1.0"),
                parking_or_dropoff=Decimal("0.0"),
                walking_distance_m=180,
                source="demo",
                checked_at=now,
            )
        )
    if session.get(AccessibilityClaim, "evt-past-1") is None:
        session.add(
            AccessibilityClaim(
                event_id="evt-past-1",
                step_free_entrance=Decimal("1.0"),
                elevator_or_ramp=Decimal("1.0"),
                accessible_restroom=Decimal("1.0"),
                accessible_seating=Decimal("0.5"),
                rest_area=Decimal("1.0"),
                parking_or_dropoff=Decimal("0.5"),
                walking_distance_m=350,
                source="demo",
                checked_at=now,
            )
        )
    if session.get(AccessibilityRequest, "req-past-1") is None:
        session.add(
            AccessibilityRequest(
                id="req-past-1",
                event_id="evt-past-1",
                attendee_id="u-att-1",
                needs_snapshot=DEMO_NEEDS.copy(),
                arrival_estimate=past_start - timedelta(minutes=30),
                note="Permintaan fiktif untuk demo verifikasi.",
                status="confirmed",
                response_decision="can_fulfill",
                response_note="Fasilitas akan disiapkan (data demo).",
                created_at=past_start - timedelta(days=5),
                responded_at=past_start - timedelta(days=4),
                confirmed_at=past_start - timedelta(days=3),
            )
        )
    session.commit()
