from fastapi import APIRouter

from app.core.dependencies import CurrentUser, SessionDep
from app.core.errors import APIError
from app.modules.verification.schemas import VerificationCreate, VerificationResponse
from app.modules.verification.service import submit_verification

router = APIRouter(tags=["verification"])


@router.post("/requests/{request_id}/verification", response_model=VerificationResponse, status_code=201)
def verify_request(
    request_id: str,
    payload: VerificationCreate,
    session: SessionDep,
    user: CurrentUser,
) -> VerificationResponse:
    if user.role != "attendee":
        raise APIError(403, "FORBIDDEN", "Hanya attendee yang dapat mengirim verifikasi")
    return submit_verification(user.id, request_id, payload, session)
