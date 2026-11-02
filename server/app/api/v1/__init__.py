"""
API v1 routers package.
"""

from .plans import router as plans_router
from .research import router as research_router
from .auth import router as auth_router
from .calendar import router as calendar_router

__all__ = [
    "plans_router",
    "research_router",
    "auth_router",
    "calendar_router",
]

