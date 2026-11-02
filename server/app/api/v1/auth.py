# ==============================================================================
# File: server/app/api/v1/auth.py
# Purpose: API router for Google OAuth authentication endpoints.
# ==============================================================================

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from app.core.config import get_frontend_url
from app.services.oauth import (
    get_authorization_url,
    exchange_code_for_tokens,
    is_google_connected,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get(
    "/google",
    summary="Initiate Google OAuth Flow",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
)
def initiate_google_oauth():
    """
    Redirects user to Google OAuth 2.0 authorization page.
    Checks environment variables and handles missing config errors.
    """
    try:
        auth_url, _ = get_authorization_url()
        return RedirectResponse(url=auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(val_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate Google OAuth flow: {str(exc)}",
        )


@router.get(
    "/google/callback",
    summary="Google OAuth Callback Handler",
)
def google_oauth_callback(
    code: Optional[str] = Query(None, description="Authorization code returned by Google"),
    error: Optional[str] = Query(None, description="OAuth error code returned by Google"),
    state: Optional[str] = Query(None, description="State verification token"),
):
    """
    Handles redirect from Google OAuth authorization page:
    - Receives authorization code
    - Exchanges code for access/refresh tokens
    - Handles OAuth denial and token exchange errors safely
    - Temporarily stores credentials in server memory for this dev phase
    - Redirects back to frontend UI with status
    """
    frontend_url = get_frontend_url()

    # 1. Handle OAuth denial or error returned by Google
    if error:
        return RedirectResponse(
            url=f"{frontend_url}/?auth_error={error}",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )

    # 2. Handle missing authorization code or state token
    if not code or not state:
        return RedirectResponse(
            url=f"{frontend_url}/?auth_error=missing_code",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )

    # 3. Exchange code for tokens & store in server memory
    try:
        exchange_code_for_tokens(code, state=state)
        return RedirectResponse(
            url=f"{frontend_url}/?auth=success",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
    except Exception as exc:
        logger.error("[OAUTH CALLBACK ERROR] Token exchange failed: %s", exc)
        return RedirectResponse(
            url=f"{frontend_url}/?auth_error=token_exchange_failed",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )


@router.get(
    "/status",
    summary="Check Google Auth Status",
)
def check_auth_status():
    """
    Returns whether Google account credentials are connected in server memory.
    """
    return {"connected": is_google_connected()}

