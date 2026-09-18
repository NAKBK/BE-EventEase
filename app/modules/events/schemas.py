"""Pydantic v2 schemas for BE-002 Event APIs.

Aligned to docs-EventEase/shared/API.md:
  BE-API-004  GET  /api/events
  BE-API-005  GET  /api/events/{event_id}
  BE-API-007  POST /api/events
  BE-API-017  POST /api/events/{event_id}/media  (response shape)
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Domain type for accessibility facility scores
#
# API.md: "Six facility claims accept exactly 0, 0.5, 1, or null."
# Literal → exact OpenAPI enum; no more long Decimal noise in Swagger.
# ---------------------------------------------------------------------------

FacilityScore = Annotated[
    Literal[0, 0.5, 1] | None,
    Field(
        description="Fulfillment score: 0 = not met, 0.5 = partial, 1 = fully met, null = unknown",
    ),
]

# Column names shared by ClaimBody field_validator
_FACILITY_FIELDS = (
    "step_free_entrance",
    "elevator_or_ramp",
    "accessible_restroom",
    "accessible_seating",
    "rest_area",
    "parking_or_dropoff",
)


# ---------------------------------------------------------------------------
# Media item  (BE-API-017 / BE-API-005 media array)
# ---------------------------------------------------------------------------

class MediaItem(BaseModel):
    """Single item in the event detail media array (BE-API-005/017)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    url: str
    uploaded_at: datetime


# ---------------------------------------------------------------------------
# Venue shapes
# ---------------------------------------------------------------------------

class VenueEmbed(BaseModel):
    """
    Venue object embedded in event list/detail responses.
    lat/lng are nullable; they are null until real coordinates exist.
    API.md BE-API-004/005: venue object includes lat and lng fields.

    NOTE: DB column names are latitude/longitude (Venue model); field names here
    are lat/lng (API contract). Always build via _build_venue_embed(), never
    model_validate() directly from a Venue ORM object.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    city: str
    address: str
    lat: float | None = Field(
        default=None,
        description="Latitude (WGS-84). null until coordinates are available.",
    )
    lng: float | None = Field(
        default=None,
        description="Longitude (WGS-84). null until coordinates are available.",
    )


class VenueCreate(BaseModel):
    """
    Inline venue supplied in POST /api/events body (BE-API-007).
    lat/lng are optional; when present, validated to [-90,90] and [-180,180].
    Out-of-range value → 422 (TASKS.md BE-002 acceptance criteria).
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    city: str = Field(min_length=1, max_length=80)
    address: str = Field(min_length=1, max_length=255)
    lat: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        description="Latitude (WGS-84), optional. Must be in [-90, 90] when provided.",
    )
    lng: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        description="Longitude (WGS-84), optional. Must be in [-180, 180] when provided.",
    )


# ---------------------------------------------------------------------------
# Organizer embed
# ---------------------------------------------------------------------------

class OrganizerEmbed(BaseModel):
    """Organizer fragment embedded in event list/detail responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    reliability_score: int | None = Field(
        default=None,
        description="0–100 feedback indicator; null when no verifications exist yet.",
    )
    sample_count: int = Field(default=0, ge=0)


# ---------------------------------------------------------------------------
# Claim shapes
# ---------------------------------------------------------------------------

class ClaimBody(BaseModel):
    """
    Accessibility claim returned in GET /api/events/{id} (BE-API-005)
    and POST /api/events 201 (BE-API-007).

    SQLAlchemy Numeric(2,1) columns return Decimal; field_validator coerces
    them to float so Pydantic's Literal check passes cleanly.
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
        """Convert Decimal from SQLAlchemy Numeric(2,1) column to plain float."""
        if isinstance(v, Decimal):
            return float(v)
        return v


class ClaimInput(BaseModel):
    """
    Claim submitted by the organizer in POST /api/events body.
    checked_at excluded — BE sets it from server time (API.md BE-API-007).
    source forced to 'organizer' in the service layer.
    """

    model_config = ConfigDict(extra="forbid")

    step_free_entrance: FacilityScore = None
    elevator_or_ramp: FacilityScore = None
    accessible_restroom: FacilityScore = None
    accessible_seating: FacilityScore = None
    rest_area: FacilityScore = None
    parking_or_dropoff: FacilityScore = None
    walking_distance_m: int | None = Field(default=None, ge=0)


# ---------------------------------------------------------------------------
# Event request body
# ---------------------------------------------------------------------------

class EventCreate(BaseModel):
    """
    POST /api/events request body — BE-API-007.
    Organizer supplies venue inline and a full accessibility claim.
    BE sets owner, status, and checked_at; body-supplied organizer_id ignored.
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
# Event response schemas
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
    """
    GET /api/events/{id} and POST /api/events 201 response (BE-API-005/007).
    media is [] until BE-009 lands; each item has the MediaItem shape (BE-API-017).
    """

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
    media: list[MediaItem] = Field(
        default_factory=list,
        description="Attached photo evidence. Empty list until BE-009 (media upload) lands.",
    )


# ---------------------------------------------------------------------------
# Match schemas (BE-003 / BE-API-006)
# Defined here so BE-003 controller and service can import from one place.
# ---------------------------------------------------------------------------

class MatchBreakdown(BaseModel):
    """Single attribute row in the BE-API-006 match breakdown."""

    attribute: str
    required: bool
    weight: float = Field(description="Relative coefficient before normalization (provisional-v1)")
    fulfillment: float | None = Field(
        description="0 / 0.5 / 1 for known values; null when claim is unknown"
    )
    label: Literal["fulfilled", "partially_fulfilled", "not_fulfilled", "unknown"]


class MatchResponse(BaseModel):
    """GET /api/events/{event_id}/match response (BE-API-006)."""

    event_id: str
    score: int = Field(ge=0, le=100, description="0–100 weighted match score")
    weight_version: str = Field(description="Weight config identifier, e.g. 'provisional-v1'")
    breakdown: list[MatchBreakdown]
    unknown_attributes: list[str]
    summary: str
