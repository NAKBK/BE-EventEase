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
