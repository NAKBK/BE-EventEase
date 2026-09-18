from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.modules.organizers.schemas import OrganizerReliability


VerificationValue = Literal["fulfilled", "partially_fulfilled", "not_fulfilled"]


class VerificationAttributes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_free_entrance: VerificationValue
    elevator_or_ramp: VerificationValue
    accessible_restroom: VerificationValue
    accessible_seating: VerificationValue
    rest_area: VerificationValue
    parking_or_dropoff: VerificationValue
    walking_distance: VerificationValue


class VerificationCreate(BaseModel):
    attributes: VerificationAttributes


class VerificationResponse(BaseModel):
    id: str
    request_id: str
    status: Literal["verified"]
    submitted_at: datetime
    organizer_reliability: OrganizerReliability
