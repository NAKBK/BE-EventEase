from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError

from app.core.config import get_settings
from app.core.errors import APIError


def create_access_token(user_id: str, role: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": user_id,
            "role": role,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["sub", "role", "iss", "aud", "iat", "exp"]},
        )
    except InvalidTokenError as exc:
        raise APIError(401, "INVALID_TOKEN", "Token tidak valid atau kedaluwarsa") from exc
    if not isinstance(payload.get("sub"), str) or payload.get("role") not in {
        "attendee",
        "organizer",
    }:
        raise APIError(401, "INVALID_TOKEN", "Token tidak valid")
    return payload
