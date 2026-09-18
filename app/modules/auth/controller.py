from fastapi import APIRouter

from app.core.dependencies import SessionDep
from app.modules.auth.schemas import DemoLoginRequest, TokenResponse
from app.modules.auth.service import demo_login


router = APIRouter(tags=["auth"])


@router.post("/demo-login", response_model=TokenResponse)
def login(payload: DemoLoginRequest, session: SessionDep) -> TokenResponse:
    """BE-API-001: issue a short-lived JWT for a seeded demo account."""
    return demo_login(payload.account, session)
