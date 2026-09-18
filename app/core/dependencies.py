from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.errors import APIError
from app.core.security import decode_access_token
from app.modules.users.models import User


bearer = HTTPBearer(auto_error=False)
SessionDep = Annotated[Session, Depends(get_session)]


def get_current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if credentials is None:
        raise APIError(401, "AUTH_REQUIRED", "Token diperlukan")
    payload = decode_access_token(credentials.credentials)
    user = session.get(User, payload["sub"])
    if user is None or user.role != payload["role"]:
        raise APIError(401, "INVALID_TOKEN", "Token tidak valid")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
