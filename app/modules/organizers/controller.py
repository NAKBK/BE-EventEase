"""BE-005 will expose /api/organizers/{organizer_id} here."""

from fastapi import APIRouter

router = APIRouter(tags=["organizers"])
