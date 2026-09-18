from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NeedSnapshot(BaseModel):
    step_free_entrance: bool
    elevator_or_ramp: bool
    accessible_restroom: bool
    accessible_seating: bool
    rest_area: bool
    parking_or_dropoff: bool
    walking_distance: str


class RequestCreate(BaseModel):
    arrival_estimate: datetime
    note: str = Field(..., max_length=500)

    @field_validator("arrival_estimate")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("arrival_estimate must include a timezone")
        return value

    @field_validator("note")
    @classmethod
    def require_note(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("note must not be blank")
        return value


class OrganizerResponseDetails(BaseModel):
    decision: Literal["can_fulfill", "partially_fulfill", "cannot_fulfill"]
    note: str
    responded_at: datetime


class RequestResponse(BaseModel):
    id: str
    event_id: str
    attendee_id: str
    status: Literal["pending", "responded", "confirmed", "closed", "verified"]
    needs_snapshot: NeedSnapshot
    arrival_estimate: datetime
    note: str
    response: OrganizerResponseDetails | None
    created_at: datetime
    confirmed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RequestItem(RequestResponse):
    event_title: str


class OrganizerResponseSubmit(BaseModel):
    decision: Literal["can_fulfill", "partially_fulfill", "cannot_fulfill"]
    note: str = Field(..., min_length=1)

    @field_validator("note")
    @classmethod
    def require_response_note(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("note must not be blank")
        return value


class AttendeeConfirmSubmit(BaseModel):
    accepted: bool
