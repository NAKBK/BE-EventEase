from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import APIError
from app.core.security import create_access_token
from app.modules.auth.schemas import TokenResponse, UserResponse
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
