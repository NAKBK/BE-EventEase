from fastapi import APIRouter

from app.core.dependencies import SessionDep
from app.modules.auth.schemas import (
    DemoLoginRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.modules.auth.service import demo_login, login_user, register_user


router = APIRouter(tags=["auth"])


@router.post("/demo-login", response_model=TokenResponse)
def login(payload: DemoLoginRequest, session: SessionDep) -> TokenResponse:
    """BE-API-001: issue a short-lived JWT for a seeded demo account."""
    return demo_login(payload.account, session)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, session: SessionDep) -> TokenResponse:
    """BE-API-014: create a real attendee/organizer account."""
    return register_user(payload, session)


@router.post("/login", response_model=TokenResponse)
def real_login(payload: LoginRequest, session: SessionDep) -> TokenResponse:
    """BE-API-015: authenticate a real account."""
    return login_user(payload, session)
