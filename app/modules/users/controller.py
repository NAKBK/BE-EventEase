"""BE-002 will expose /api/me/needs from this module."""

from fastapi import APIRouter

router = APIRouter(tags=["needs"])
