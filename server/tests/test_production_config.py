# ==============================================================================
# File: server/tests/test_production_config.py
# Purpose: Pytest unit tests verifying production readiness configuration.
# ==============================================================================

import os
import pytest
from app.services.oauth import configure_oauth_transport
from app.main import get_cors_origins, get_frontend_url


def test_development_environment_enables_insecure_oauth_transport(monkeypatch):
    """
    Verifies that when ENVIRONMENT=development, OAUTHLIB_INSECURE_TRANSPORT is set to '1'.
    """
    monkeypatch.setenv("ENVIRONMENT", "development")
    configure_oauth_transport()
    assert os.environ.get("OAUTHLIB_INSECURE_TRANSPORT") == "1"


def test_production_environment_disables_insecure_oauth_transport(monkeypatch):
    """
    Verifies that when ENVIRONMENT=production (or unconfigured), OAUTHLIB_INSECURE_TRANSPORT is NOT enabled.
    """
    # Test explicitly set to production
    monkeypatch.setenv("ENVIRONMENT", "production")
    configure_oauth_transport()
    assert "OAUTHLIB_INSECURE_TRANSPORT" not in os.environ

    # Test unconfigured / missing ENVIRONMENT
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    configure_oauth_transport()
    assert "OAUTHLIB_INSECURE_TRANSPORT" not in os.environ


def test_frontend_url_read_from_environment(monkeypatch):
    """
    Verifies that FRONTEND_URL is read from environment variables, defaulting to localhost if absent.
    """
    # 1. Custom production URL
    monkeypatch.setenv("FRONTEND_URL", "https://app.pathai.example.com")
    assert get_frontend_url() == "https://app.pathai.example.com"

    # 2. Fallback to localhost when unconfigured
    monkeypatch.delenv("FRONTEND_URL", raising=False)
    assert get_frontend_url() == "http://localhost:5173"


def test_cors_allowed_origins_parsing(monkeypatch):
    """
    Verifies parsing of CORS_ALLOWED_ORIGINS comma-separated URLs and default fallback.
    """
    # 1. Custom CORS origins
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://app.pathai.example.com, https://admin.pathai.example.com"
    )
    origins = get_cors_origins()
    assert origins == [
        "https://app.pathai.example.com",
        "https://admin.pathai.example.com",
    ]

    # 2. Fallback to default localhost origins when unconfigured
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    default_origins = get_cors_origins()
    assert default_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_cors_origins_never_includes_wildcard_automatically(monkeypatch):
    """
    Verifies wildcard '*' is never automatically used as a default origin.
    """
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    origins = get_cors_origins()
    assert "*" not in origins
