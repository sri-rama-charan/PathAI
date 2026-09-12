# ==============================================================================
# File: server/app/services/oauth.py
# Purpose: Service module handling Google OAuth 2.0 flow for PathAI.
#
# Scopes:
#   Request only minimum Google scopes for upcoming Google Docs feature:
#   - https://www.googleapis.com/auth/documents
#   - https://www.googleapis.com/auth/drive.file
#   - openid, userinfo.email (for identification)
#   NO Google Calendar permissions requested.
#
# Storage:
#   Credentials are stored in server memory dict (_token_store) for this dev phase.
# ==============================================================================

import os
from typing import Dict, Any, Tuple, Optional
from google_auth_oauthlib.flow import Flow

# Enable insecure transport for http:// localhost in development
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Temporary in-memory token store for development phase (No DB used)
_token_store: Dict[str, Any] = {}

# Scopes restricted strictly to Google Docs integration & basic user identification
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]


def get_oauth_config() -> Tuple[str, str, str]:
    """
    Validates and retrieves Google OAuth configuration from environment variables.
    
    Raises:
        ValueError: If any required Google OAuth environment variable is missing or empty.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "").strip()

    missing = []
    if not client_id:
        missing.append("GOOGLE_CLIENT_ID")
    if not client_secret:
        missing.append("GOOGLE_CLIENT_SECRET")
    if not redirect_uri:
        missing.append("GOOGLE_REDIRECT_URI")

    if missing:
        raise ValueError(
            f"Google OAuth configuration error: Missing required environment variable(s): {', '.join(missing)}. "
            "Please configure them in your server .env file."
        )

    return client_id, client_secret, redirect_uri


def _build_client_config() -> dict:
    """
    Constructs the client configuration dictionary for google-auth-oauthlib Flow.
    """
    client_id, client_secret, redirect_uri = get_oauth_config()
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }


def get_authorization_url() -> Tuple[str, str]:
    """
    Generates the Google OAuth authorization URL and state token for user redirection.

    Returns:
        Tuple[authorization_url, state]
    """
    client_config = _build_client_config()
    _, _, redirect_uri = get_oauth_config()

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return authorization_url, state


def exchange_code_for_tokens(code: str) -> dict:
    """
    Exchanges authorization code received from Google callback for access/refresh tokens.
    Stores the resulting credentials temporarily in server memory.

    Args:
        code: Authorization code string from Google OAuth callback.

    Returns:
        dict: Credential details (access_token, refresh_token, etc.).
    
    Raises:
        ValueError: If authorization code is missing or empty.
        RuntimeError: If code exchange with Google fails.
    """
    cleaned_code = code.strip() if code else ""
    if not cleaned_code:
        raise ValueError("Missing authorization code. Cannot exchange for tokens.")

    client_config = _build_client_config()
    _, _, redirect_uri = get_oauth_config()

    try:
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
        flow.fetch_token(code=cleaned_code)
        credentials = flow.credentials

        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
        }

        # Temporarily store credentials in server memory for this dev phase
        _token_store["google_credentials"] = token_data
        return token_data

    except Exception as exc:
        raise RuntimeError(f"Failed to exchange OAuth code for Google tokens: {str(exc)}")


def is_google_connected() -> bool:
    """
    Checks if Google account credentials are currently stored in server memory.
    """
    creds = _token_store.get("google_credentials")
    return bool(creds and creds.get("token"))


def get_stored_credentials() -> Optional[dict]:
    """
    Retrieves stored Google credentials from server memory.
    """
    return _token_store.get("google_credentials")


def clear_stored_credentials() -> None:
    """
    Clears stored Google credentials from server memory.
    """
    _token_store.pop("google_credentials", None)
