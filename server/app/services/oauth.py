# ==============================================================================
# File: server/app/services/oauth.py
# Purpose: Service facade for Google OAuth authentication and state verification.
# ==============================================================================

from typing import Tuple, Optional, Dict, Any
from app.integrations.google_oauth import (
    configure_oauth_transport,
    get_oauth_config,
    get_authorization_url,
    exchange_code_for_tokens,
    is_google_connected,
    get_stored_credentials,
    clear_stored_credentials,
    get_authenticated_credentials,
    SCOPES,
)

__all__ = [
    "configure_oauth_transport",
    "get_oauth_config",
    "get_authorization_url",
    "exchange_code_for_tokens",
    "is_google_connected",
    "get_stored_credentials",
    "clear_stored_credentials",
    "get_authenticated_credentials",
    "SCOPES",
]
