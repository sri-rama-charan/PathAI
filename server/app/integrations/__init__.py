"""
PathAI external integrations package.
Encapsulates external API communication, SDK initialization, and request/response dispatching.
"""

from .gemini import get_gemini_client, generate_structured_content
from .tavily import get_tavily_api_key, execute_tavily_search
from .google_oauth import (
    configure_oauth_transport,
    get_oauth_config,
    get_authorization_url,
    exchange_code_for_tokens,
    is_google_connected,
    get_stored_credentials,
    clear_stored_credentials,
    get_authenticated_credentials,
)
from .google_docs import create_document, verify_document
from .google_calendar import insert_event, verify_event

__all__ = [
    "get_gemini_client",
    "generate_structured_content",
    "get_tavily_api_key",
    "execute_tavily_search",
    "configure_oauth_transport",
    "get_oauth_config",
    "get_authorization_url",
    "exchange_code_for_tokens",
    "is_google_connected",
    "get_stored_credentials",
    "clear_stored_credentials",
    "get_authenticated_credentials",
    "create_document",
    "verify_document",
    "insert_event",
    "verify_event",
]

