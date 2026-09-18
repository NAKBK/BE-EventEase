"""BE-002/003 will expose /api/events endpoints here."""

from fastapi import APIRouter

router = APIRouter(tags=["events"])
