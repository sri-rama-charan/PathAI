# ==============================================================================
# File: server/app/core/config.py
# Purpose: Central application configuration and environment variable management.
# ==============================================================================

import os
import logging
from pathlib import Path
from typing import List
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Resolve path to server directory and load environment variables
SERVER_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(SERVER_DIR / ".env", override=True)
load_dotenv(override=True)

# Required configuration variables for production startup
REQUIRED_PRODUCTION_VARS: List[str] = [
    "GEMINI_API_KEY",
    "TAVILY_API_KEY",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_REDIRECT_URI",
    "FRONTEND_URL",
]

# Sensitive placeholder prefixes to detect unconfigured template values
PLACEHOLDER_PREFIXES: List[str] = [
    "your_",
    "tvly-your",
]


def validate_production_environment() -> None:
    """
    Validates required environment variables when running in production mode (ENVIRONMENT=production).
    Raises RuntimeError listing only missing variable NAMES if any are missing or set to placeholders.
    Never logs or exposes actual variable values.
    """
    env_name = os.getenv("ENVIRONMENT", "").strip().lower()
    if env_name != "production":
        return

    missing_vars = []
    for var_name in REQUIRED_PRODUCTION_VARS:
        val = os.getenv(var_name, "").strip()
        if not val or any(val.startswith(ph) for ph in PLACEHOLDER_PREFIXES):
            missing_vars.append(var_name)

    if missing_vars:
        error_msg = f"Production startup failed: Missing or invalid required environment variable(s): {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    logger.info("Production environment validation successful. All required configuration variables are set.")


def get_cors_origins() -> List[str]:
    """
    Parses CORS allowed origins from CORS_ALLOWED_ORIGINS environment variable.
    Format: comma-separated list of origin URLs.
    
    If CORS_ALLOWED_ORIGINS is missing or empty, defaults safely to development origins:
    ["http://localhost:5173", "http://127.0.0.1:5173"].
    
    Ensures wildcard '*' is never automatically included.
    """
    raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
    if raw_origins:
        parsed = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
        if parsed:
            return parsed

    return ["http://localhost:5173", "http://127.0.0.1:5173"]


def get_frontend_url() -> str:
    """
    Retrieves the frontend web application URL for post-OAuth redirects.
    Defaults to http://localhost:5173 if FRONTEND_URL is not configured.
    """
    return os.getenv("FRONTEND_URL", "http://localhost:5173").strip() or "http://localhost:5173"


def get_database_url() -> str:
    """
    Retrieves and normalizes DATABASE_URL from environment variables.
    Handles Render's 'postgres://' prefix by converting to 'postgresql://'.
    Falls back to a local SQLite database for development/testing if unset.
    """
    raw_url = os.getenv("DATABASE_URL", "").strip()
    if not raw_url:
        db_path = SERVER_DIR / "pathai.db"
        logger.info("DATABASE_URL not set. Falling back to local SQLite: %s", db_path)
        return f"sqlite:///{db_path}"

    # Render uses postgres:// which SQLAlchemy 1.4+ / 2.0 deprecated
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)

    return raw_url

