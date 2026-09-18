from typing import Literal

from pydantic import BaseModel, ConfigDict


class DemoLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account: Literal["attendee", "organizer"]


class UserResponse(BaseModel):
    id: str
    name: str
    role: Literal["attendee", "organizer"]


class TokenResponse(BaseModel):
    token: str
    user: UserResponse
