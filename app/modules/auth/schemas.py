import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str = Field(min_length=8)
    name: str = Field(min_length=1, max_length=120)
    role: Literal["attendee", "organizer"]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not _EMAIL_PATTERN.match(value):
            raise ValueError("invalid email format")
        return value


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()
