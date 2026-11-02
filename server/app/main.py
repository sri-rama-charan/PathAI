# ==============================================================================
# File: server/app/main.py
# Purpose: Entry point for the PathAI FastAPI backend server.
#
# What this file does:
# 1. Creates the FastAPI application instance and manages application lifecycle.
# 2. Configures security middleware and CORS for React frontend.
# 3. Mounts the central API router (including plans, research, auth, and calendar routes).
# 4. Exposes GET /: Root health check endpoint.
# 5. Exposes GET /docs: Interactive Swagger UI.
# ==============================================================================

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import (
    REQUIRED_PRODUCTION_VARS,
    PLACEHOLDER_PREFIXES,
    validate_production_environment,
    get_cors_origins,
    get_frontend_url,
)
from app.db.database import init_db
from app.api.router import api_router


# Configure application logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup validation, database initialization,
    and shutdown lifecycle hooks.
    """
    validate_production_environment()
    try:
        init_db()
    except Exception as exc:
        logger.warning("Could not auto-initialize database on startup: %s", exc)
    yield


# ------------------------------------------------------------------------------
# 1. Create the FastAPI Application
# ------------------------------------------------------------------------------
app = FastAPI(
    title="PathAI Backend",
    description="Backend API for PathAI — AI Learning Path Generator",
    version="0.3.0",
    lifespan=lifespan,
)


# ------------------------------------------------------------------------------
# 2. Security Headers Middleware
# ------------------------------------------------------------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Attaches security headers to every HTTP response:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - Referrer-Policy: strict-origin-when-cross-origin
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app.add_middleware(SecurityHeadersMiddleware)


# ------------------------------------------------------------------------------
# 3. Configure CORS (Cross-Origin Resource Sharing)
# ------------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------------------
# 4. Global Production Exception Handler
# ------------------------------------------------------------------------------
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled exceptions.
    In production (ENVIRONMENT=production), returns a generic 500 error response
    without leaking internal stack traces or implementation details to clients.
    In development mode, re-raises to preserve standard debugging behavior.
    """
    env_name = os.getenv("ENVIRONMENT", "").strip().lower()
    if env_name == "production":
        logger.error("[PRODUCTION UNHANDLED EXCEPTION] Path: %s | Error: %s", request.url.path, exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected internal server error occurred."},
        )

    raise exc


# ------------------------------------------------------------------------------
# 5. Root Health Check Endpoint
# ------------------------------------------------------------------------------
@app.get("/", summary="Root Health Check")
def read_root():
    """
    Root endpoint for PathAI.
    """
    return {
        "status": "online",
        "message": "PathAI backend is running successfully!",
        "service": "PathAI",
        "docs_url": "/docs",
    }


# ------------------------------------------------------------------------------
# 6. Include Modular API Routers
# ------------------------------------------------------------------------------
app.include_router(api_router)
