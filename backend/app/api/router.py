"""Aggregates all v1 routers. The `/api/v1` prefix is applied where this
router is included (see app.main), keeping the prefix configurable via
settings rather than hardcoded here.
"""

from fastapi import APIRouter

from app.api.v1 import analyses, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(analyses.router, tags=["analyses"])
