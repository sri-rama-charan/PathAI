# ==============================================================================
# File: server/app/integrations/google_calendar.py
# Purpose: Google Calendar API v3 communication, event creation, and verification.
# ==============================================================================

from typing import Dict, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def insert_event(
    event_body: Dict[str, Any],
    credentials: Any,
    calendar_id: str = "primary",
) -> Dict[str, Any]:
    """
    Inserts a single event into Google Calendar via API v3.
    
    Args:
        event_body: Formatted Google Calendar event payload.
        credentials: Authenticated Google Credentials instance.
        calendar_id: Target calendar identifier (defaults to "primary").
        
    Returns:
        Dict[str, Any]: Created Google Calendar event resource.
        
    Raises:
        RuntimeError: If calendar event creation fails.
    """
    try:
        calendar_service = build("calendar", "v3", credentials=credentials)
        return (
            calendar_service.events()
            .insert(calendarId=calendar_id, body=event_body)
            .execute()
        )
    except HttpError as http_err:
        reason = http_err.reason if hasattr(http_err, "reason") else str(http_err)
        status_code = http_err.resp.status if hasattr(http_err, "resp") else 500
        raise RuntimeError(f"Google Calendar API error (HTTP {status_code}): {reason}") from http_err
    except Exception as exc:
        raise RuntimeError(f"Failed to create Google Calendar event: {str(exc)}") from exc


def verify_event(
    event_id: str,
    credentials: Any,
    calendar_id: str = "primary",
) -> Dict[str, Any]:
    """
    Verifies that a Google Calendar event exists and is accessible via events().get().
    
    Args:
        event_id: Unique Google Calendar event ID string.
        credentials: Authenticated Google Credentials instance.
        calendar_id: Target calendar identifier (defaults to "primary").
        
    Returns:
        Dict[str, Any]: Contains 'verified', 'event_id', 'summary', and optional 'error'.
    """
    cleaned_id = event_id.strip() if event_id else ""
    if not cleaned_id:
        return {
            "verified": False,
            "event_id": "",
            "summary": "",
            "error": "Event ID cannot be empty for verification.",
        }

    try:
        calendar_service = build("calendar", "v3", credentials=credentials)
        event = (
            calendar_service.events()
            .get(calendarId=calendar_id, eventId=cleaned_id)
            .execute()
        )

        retrieved_id = event.get("id", cleaned_id)
        summary = event.get("summary", "")

        if retrieved_id == cleaned_id:
            return {
                "verified": True,
                "event_id": retrieved_id,
                "summary": summary,
                "error": None,
            }
        else:
            return {
                "verified": False,
                "event_id": cleaned_id,
                "summary": summary,
                "error": "Event ID mismatch during verification.",
            }

    except HttpError as http_err:
        reason = http_err.reason if hasattr(http_err, "reason") else str(http_err)
        status_code = http_err.resp.status if hasattr(http_err, "resp") else 500
        return {
            "verified": False,
            "event_id": cleaned_id,
            "summary": "",
            "error": f"Google Calendar API verification error (HTTP {status_code}): {reason}",
        }
    except Exception as exc:
        return {
            "verified": False,
            "event_id": cleaned_id,
            "summary": "",
            "error": f"Failed to verify Google Calendar event accessibility: {str(exc)}",
        }

