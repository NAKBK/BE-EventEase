"""BE-004 will expose /api/requests and event request actions here."""

from fastapi import APIRouter

router = APIRouter(tags=["requests"])
