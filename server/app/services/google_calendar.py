# ==============================================================================
# File: server/app/services/google_calendar.py
# Purpose: Compatibility shim — re-exports from app.services.calendar_service.
#
# NOTE: Business logic has moved to app.services.calendar_service (Stage 5).
#       This shim preserves existing import paths used by API routers.
# ==============================================================================

from app.services.calendar_service import (  # noqa: F401
    _format_event_description,
    create_calendar_events_for_plan,
)

# verify_calendar_event was defined here in Stage 4 — keep it available
from app.integrations.google_oauth import get_authenticated_credentials
from app.integrations.google_calendar import verify_event
from typing import Dict, Any


def verify_calendar_event(event_id: str) -> Dict[str, Any]:
    """
    Verifies that a calendar event exists and is accessible.
    Preserved here for backward compatibility.
    """
    creds = get_authenticated_credentials()
    return verify_event(event_id=event_id, credentials=creds)
