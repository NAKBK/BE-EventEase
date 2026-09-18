"""Pydantic v2 schemas for BE-002 Event APIs.

Aligned to shared/API.md:
  BE-API-004  GET  /api/events
  BE-API-005  GET  /api/events/{event_id}
  BE-API-007  POST /api/events
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Domain type for accessibility facility scores
#
# API.md: "Six facility claims accept exactly 0, 0.5, 1, or null."
# Using Literal produces an exact OpenAPI enum in Swagger — no more long Decimal noise.
# Annotated alias gives us a reusable type with a clean schema description.
# ---------------------------------------------------------------------------

FacilityScore = Annotated[
    Literal[0, 0.5, 1] | None,
    Field(
        description="Organizer fulfillment score: 0 = not met, 0.5 = partial, 1 = fully met, null = unknown",
    ),
]

# Facility column names — used by the shared validator below
_FACILITY_FIELDS = (
    "step_free_entrance",
    "elevator_or_ramp",
    "accessible_restroom",
    "accessible_seating",
    "rest_area",
    "parking_or_dropoff",
)


# ---------------------------------------------------------------------------
# Shared / nested shapes
# ---------------------------------------------------------------------------

class VenueEmbed(BaseModel):
    """Venue object as it appears inside event responses (API.md §BE-API-004/005)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    city: str
    address: str


class OrganizerEmbed(BaseModel):
    """Organizer fragment embedded in event list/detail responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    reliability_score: int | None = Field(
        default=None,
        description="0–100 feedback indicator, null when no verifications exist yet",
    )
    sample_count: int = Field(default=0, ge=0)


class ClaimBody(BaseModel):
    """
    Accessibility claim returned in GET /api/events/{id} (BE-API-005)
    and POST /api/events 201 (BE-API-007).
    Six facility values accept 0 | 0.5 | 1 | null exactly (API.md §Claim).
    walking_distance_m is a non-negative integer or null.

    SQLAlchemy Numeric(2,1) columns return Decimal values; the field_validator
    below coerces them to float so Pydantic's Literal check passes cleanly.
    """

    model_config = ConfigDict(from_attributes=True)

    step_free_entrance: FacilityScore = None
    elevator_or_ramp: FacilityScore = None
    accessible_restroom: FacilityScore = None
    accessible_seating: FacilityScore = None
    rest_area: FacilityScore = None
    parking_or_dropoff: FacilityScore = None
    walking_distance_m: int | None = Field(default=None, ge=0)
    source: Literal["organizer", "open_data", "demo"]
    checked_at: datetime

    @field_validator(*_FACILITY_FIELDS, mode="before")
    @classmethod
    def coerce_decimal_to_float(cls, v: object) -> object:
        """Convert Decimal from SQLAlchemy Numeric column to plain float/int."""
        if isinstance(v, Decimal):
            return float(v)
        return v


class ClaimInput(BaseModel):
    """
    Accessibility claim submitted by the organizer in POST /api/events body (BE-API-007).
    checked_at is excluded — BE always sets it from server time (API.md BE-API-007).
    source is always forced to 'organizer' in the service layer.
    """

    model_config = ConfigDict(extra="forbid")

    step_free_entrance: FacilityScore = None
    elevator_or_ramp: FacilityScore = None
    accessible_restroom: FacilityScore = None
    accessible_seating: FacilityScore = None
    rest_area: FacilityScore = None
    parking_or_dropoff: FacilityScore = None
    walking_distance_m: int | None = Field(default=None, ge=0)


class VenueCreate(BaseModel):
    """Inline venue object inside POST /api/events body (BE-API-007)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    city: str = Field(min_length=1, max_length=80)
    address: str = Field(min_length=1, max_length=255)


# ---------------------------------------------------------------------------
# Request body
# ---------------------------------------------------------------------------

class EventCreate(BaseModel):
    """
    POST /api/events request body — BE-API-007.
    Organizer supplies venue inline and a full accessibility claim.
    BE sets owner, status, and checked_at; body-supplied organizer_id is ignored.
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=180)
    description: str = Field(default="", max_length=5000)
    starts_at: datetime
    ends_at: datetime
    venue: VenueCreate
    claim: ClaimInput

    @model_validator(mode="after")
    def ends_after_starts(self) -> "EventCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at harus setelah starts_at")
        return self


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class EventListItem(BaseModel):
    """Single item inside GET /api/events items array (BE-API-004)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    starts_at: datetime
    status: Literal["upcoming", "completed"]
    venue: VenueEmbed
    organizer: OrganizerEmbed


class EventListResponse(BaseModel):
    """GET /api/events 200 envelope (BE-API-004)."""

    items: list[EventListItem]
    total: int
    limit: int
    offset: int


class EventDetail(BaseModel):
    """GET /api/events/{id} and POST /api/events 201 response (BE-API-005/007)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    starts_at: datetime
    ends_at: datetime
    status: Literal["upcoming", "completed"]
    venue: VenueEmbed
    organizer: OrganizerEmbed
    claim: ClaimBody | None = None
"""BE-002/003 will add event and matching API schemas here."""

from pydantic import BaseModel


class MatchBreakdown(BaseModel):
    attribute: str
    required: bool
    weight: float
    fulfillment: float | None
    label: str


class MatchResponse(BaseModel):
    event_id: str
    score: int
    weight_version: str
    breakdown: list[MatchBreakdown]
    unknown_attributes: list[str]
    summary: str
