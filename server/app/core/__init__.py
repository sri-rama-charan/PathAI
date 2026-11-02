# ==============================================================================
# File: server/app/core/__init__.py
# Purpose: Exports core configuration module elements.
# ==============================================================================

from app.core.config import (
    SERVER_DIR,
    REQUIRED_PRODUCTION_VARS,
    PLACEHOLDER_PREFIXES,
    validate_production_environment,
    get_cors_origins,
    get_frontend_url,
    get_database_url,
)

__all__ = [
    "SERVER_DIR",
    "REQUIRED_PRODUCTION_VARS",
    "PLACEHOLDER_PREFIXES",
    "validate_production_environment",
    "get_cors_origins",
    "get_frontend_url",
    "get_database_url",
]

