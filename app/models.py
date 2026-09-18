"""Import all model classes so Alembic sees the complete schema."""

from app.modules.accessibility_requests.models import AccessibilityRequest
from app.modules.events.models import AccessibilityClaim, Event, EventMedia
from app.modules.organizers.models import Organizer
from app.modules.users.models import NeedProfile, User
from app.modules.venues.models import Venue
from app.modules.verification.models import Verification

__all__ = [
    "User",
    "NeedProfile",
    "Organizer",
    "Venue",
    "Event",
    "EventMedia",
    "AccessibilityClaim",
    "AccessibilityRequest",
    "Verification",
]
