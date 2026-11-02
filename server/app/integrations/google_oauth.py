# ==============================================================================
# File: server/app/integrations/google_oauth.py
# Purpose: Google OAuth 2.0 SDK Flow, token storage, and credential management.
# ==============================================================================

import os
from typing import Dict, Any, Tuple, Optional
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


def configure_oauth_transport() -> None:
    """
    Configures OAUTHLIB_INSECURE_TRANSPORT environment variable.
    Enables insecure HTTP transport ONLY when ENVIRONMENT is explicitly set to 'development'.
    Safe by default: if ENVIRONMENT is missing, 'production', or anything else,
    insecure transport is NOT enabled (and removed from os.environ if present).
    """
    env_name = os.getenv("ENVIRONMENT", "").strip().lower()
    if env_name == "development":
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    else:
        os.environ.pop("OAUTHLIB_INSECURE_TRANSPORT", None)


# Configure OAuth transport at module load time
configure_oauth_transport()

# Temporary in-memory token store for development phase (No DB used)
_token_store: Dict[str, Any] = {}

# Temporary in-memory state store for PKCE code_verifier mapping (state -> {"code_verifier": verifier})
_oauth_state_store: Dict[str, dict] = {}

# Scopes for Google Docs, Google Calendar events, and basic user identification
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/calendar.events",
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


def build_client_config() -> dict:
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
    Stores the PKCE code_verifier in server memory linked to the generated state.

    Returns:
        Tuple[authorization_url, state]
    """
    client_config = build_client_config()
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

    if state and flow.code_verifier:
        _oauth_state_store[state] = {
            "code_verifier": flow.code_verifier,
        }

    return authorization_url, state


def exchange_code_for_tokens(code: str, state: Optional[str] = None) -> dict:
    """
    Exchanges authorization code received from Google callback for access/refresh tokens.
    Retrieves the stored PKCE code_verifier using the matching state parameter.
    Stores the resulting credentials temporarily in server memory.

    Args:
        code: Authorization code string from Google OAuth callback.
        state: OAuth state string from Google OAuth callback.

    Returns:
        dict: Credential details (access_token, refresh_token, etc.).
    
    Raises:
        ValueError: If authorization code or state is missing/invalid.
        RuntimeError: If code exchange with Google fails.
    """
    cleaned_code = code.strip() if code else ""
    if not cleaned_code:
        raise ValueError("Missing authorization code. Cannot exchange for tokens.")

    cleaned_state = state.strip() if state else ""
    if not cleaned_state:
        raise ValueError("Missing OAuth state parameter. Cannot exchange for tokens.")

    state_data = _oauth_state_store.pop(cleaned_state, None)
    if not state_data or "code_verifier" not in state_data:
        raise ValueError("Invalid or expired OAuth state parameter.")

    code_verifier = state_data["code_verifier"]

    client_config = build_client_config()
    _, _, redirect_uri = get_oauth_config()

    try:
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
        flow.code_verifier = code_verifier
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


def get_authenticated_credentials() -> Credentials:
    """
    Retrieves and refreshes stored Google OAuth credentials from server memory.

    Raises:
        ValueError: If Google account is not connected or credentials are missing/expired.
    """
    if not is_google_connected():
        raise ValueError(
            "Google account is not connected. Please connect your Google account first."
        )

    stored_creds = get_stored_credentials()
    if not stored_creds:
        raise ValueError(
            "Google OAuth credentials missing from server memory. Please reconnect your Google account."
        )

    try:
        creds = Credentials(
            token=stored_creds.get("token"),
            refresh_token=stored_creds.get("refresh_token"),
            token_uri=stored_creds.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=stored_creds.get("client_id"),
            client_secret=stored_creds.get("client_secret"),
            scopes=stored_creds.get("scopes"),
        )

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Update active token in server memory
            stored_creds["token"] = creds.token

        return creds

    except Exception as auth_exc:
        raise ValueError(
            f"Google authentication failed or credentials expired: {str(auth_exc)}. Please reconnect."
        )

