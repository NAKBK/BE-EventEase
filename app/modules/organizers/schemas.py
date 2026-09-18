from datetime import datetime

from pydantic import BaseModel


class OrganizerReliability(BaseModel):
    score: int | None
    sample_count: int
    window_size: int = 20
    updated_at: datetime | None


class OrganizerProfileResponse(BaseModel):
    id: str
    name: str
    reliability: OrganizerReliability
