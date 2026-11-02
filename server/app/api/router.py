# ==============================================================================
# File: server/app/api/router.py
# Purpose: Master API router aggregating modular sub-routers for PathAI.
# ==============================================================================

from fastapi import APIRouter

from app.api.v1.plans import router as plans_router
from app.api.v1.research import router as research_router
from app.api.v1.auth import router as auth_router
from app.api.v1.calendar import router as calendar_router

api_router = APIRouter(prefix="/api")

# Register individual sub-routers
api_router.include_router(plans_router)
api_router.include_router(research_router)
api_router.include_router(auth_router)
api_router.include_router(calendar_router)

