"""Pydantic v2 schemas for BE-002 Need Profile APIs.

Aligned to shared/API.md:
  BE-API-002  GET /api/me/needs
  BE-API-003  PUT /api/me/needs
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


WalkingDistance = Literal["short", "moderate", "any"]


# ---------------------------------------------------------------------------
# Inner profile shape  (shared/API.md §NeedProfile)
# ---------------------------------------------------------------------------

class NeedProfileBody(BaseModel):
    """
    The seven-key NeedProfile shape used in both request and response.
    from_attributes=True so model_validate() works directly from SQLAlchemy rows.
    extra is NOT forbidden here so FastAPI can compose it as a nested response model.
    """

    model_config = ConfigDict(from_attributes=True)

    step_free_entrance: bool
    elevator_or_ramp: bool
    accessible_restroom: bool
    accessible_seating: bool
    rest_area: bool
    parking_or_dropoff: bool
    walking_distance: WalkingDistance


# ---------------------------------------------------------------------------
# Request body (PUT) — separate class so FastAPI resolves it independently
# ---------------------------------------------------------------------------

class NeedProfileUpsert(BaseModel):
    """
    PUT /api/me/needs request body.
    All seven keys are required (API.md: 'All seven keys are required on PUT').
    extra='forbid' rejects unknown fields on input only.
    """

    model_config = ConfigDict(extra="forbid")

    step_free_entrance: bool
    elevator_or_ramp: bool
    accessible_restroom: bool
    accessible_seating: bool
    rest_area: bool
    parking_or_dropoff: bool
    walking_distance: WalkingDistance


# ---------------------------------------------------------------------------
# Response envelope  (API.md §BE-API-002)
# ---------------------------------------------------------------------------

class NeedProfileResponse(BaseModel):
    """
    GET /api/me/needs and PUT /api/me/needs 200 response envelope.

    Shape per API.md BE-API-002:
      { "profile": <NeedProfile> | null, "updated_at": "<ISO8601>" | null }

    profile and updated_at are both null before the first save.
    """

    profile: NeedProfileBody | None = None
    updated_at: datetime | None = None