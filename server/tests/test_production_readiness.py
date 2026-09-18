# ==============================================================================
# File: server/tests/test_production_readiness.py
# Purpose: Pytest unit tests for production hardening: security headers, exception masking, startup validation.
# ==============================================================================

import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.main import app, validate_production_environment

client = TestClient(app)


def test_security_headers_present_on_responses():
    """
    Verifies that security headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy)
    are attached to HTTP responses.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    # Verify legacy X-XSS-Protection header is NOT present
    assert "X-XSS-Protection" not in response.headers


def test_production_exception_masking_returns_generic_500(monkeypatch):
    """
    Verifies that in production mode (ENVIRONMENT=production), unhandled exceptions return
    a generic sanitized HTTP 500 response without exposing stack traces.
    """
    monkeypatch.setenv("ENVIRONMENT", "production")

    test_app = FastAPI()
    
    # Import and attach handlers from main
    from app.main import SecurityHeadersMiddleware, unhandled_exception_handler
    test_app.add_middleware(SecurityHeadersMiddleware)
    test_app.add_exception_handler(Exception, unhandled_exception_handler)

    @test_app.get("/test-error")
    def trigger_error():
        raise RuntimeError("Secret internal database connection string: postgresql://admin:secret@db:5432/main")

    test_client = TestClient(test_app, raise_server_exceptions=False)
    response = test_client.get("/test-error")

    assert response.status_code == 500
    body = response.json()
    assert body == {"detail": "An unexpected internal server error occurred."}
    assert "Secret internal database" not in response.text


def test_production_startup_validation_success(monkeypatch):
    """
    Verifies that production startup validation succeeds when all required environment variables are set.
    """
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("GEMINI_API_KEY", "prod_gemini_key_12345")
    monkeypatch.setenv("TAVILY_API_KEY", "prod_tavily_key_12345")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "prod_client_id.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "prod_client_secret_12345")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "https://api.pathai.example.com/api/auth/google/callback")
    monkeypatch.setenv("FRONTEND_URL", "https://app.pathai.example.com")

    # Should run cleanly without raising RuntimeError
    validate_production_environment()


def test_production_startup_validation_fails_on_missing_or_placeholder_vars(monkeypatch):
    """
    Verifies that missing or placeholder environment variables raise RuntimeError during production startup validation.
    """
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("GEMINI_API_KEY", "your_gemini_api_key_here")  # Placeholder
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)  # Missing

    with pytest.raises(RuntimeError) as exc_info:
        validate_production_environment()

    err_str = str(exc_info.value)
    assert "GEMINI_API_KEY" in err_str
    assert "TAVILY_API_KEY" in err_str
    # Ensure no secret values are leaked in the error message
    assert "your_gemini_api_key_here" not in err_str


def test_development_mode_remains_functional_without_enforced_startup_check(monkeypatch):
    """
    Verifies that in development mode (ENVIRONMENT=development or unconfigured), missing production vars do NOT block startup.
    """
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    # Should not raise RuntimeError in development mode
    validate_production_environment()
