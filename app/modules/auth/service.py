import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import APIError
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.modules.organizers.models import Organizer
from app.modules.users.models import User


DEMO_USER_IDS = {"attendee": "u-att-1", "organizer": "u-org-1"}


def demo_login(account: str, session: Session) -> TokenResponse:
    if not get_settings().enable_demo_login:
        raise APIError(403, "DEMO_LOGIN_DISABLED", "Demo login tidak aktif")
    user = session.get(User, DEMO_USER_IDS[account])
    if user is None or user.role != account:
        raise APIError(503, "DEMO_DATA_MISSING", "Akun demo belum tersedia")
    return TokenResponse(
        token=create_access_token(user.id, user.role),
        user=UserResponse(id=user.id, name=user.display_name, role=user.role),
    )


def register_user(payload: RegisterRequest, session: Session) -> TokenResponse:
    existing = session.execute(
        select(User).where(User.email == payload.email)
    ).scalar_one_or_none()
    if existing is not None:
        raise APIError(409, "EMAIL_TAKEN", "Email sudah terdaftar")

    user = User(
        id=str(uuid.uuid4()),
        display_name=payload.name,
        role=payload.role,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    session.flush()  # write user so organizers.owner_user_id FK resolves

    if payload.role == "organizer":
        session.add(
            Organizer(id=str(uuid.uuid4()), owner_user_id=user.id, name=payload.name)
        )

    session.commit()

    return TokenResponse(
        token=create_access_token(user.id, user.role),
        user=UserResponse(id=user.id, name=user.display_name, role=user.role),
    )


def login_user(payload: LoginRequest, session: Session) -> TokenResponse:
    user = session.execute(
        select(User).where(User.email == payload.email)
    ).scalar_one_or_none()
    if (
        user is None
        or user.password_hash is None
        or not verify_password(payload.password, user.password_hash)
    ):
        raise APIError(401, "INVALID_CREDENTIALS", "Email atau password salah")

    return TokenResponse(
        token=create_access_token(user.id, user.role),
        user=UserResponse(id=user.id, name=user.display_name, role=user.role),
    )
