"""Venue data is exposed through event endpoints in BE-002."""

from fastapi import APIRouter

router = APIRouter(tags=["venues"])
