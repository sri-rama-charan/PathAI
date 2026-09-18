# ==============================================================================
# File: server/app/services/google_calendar.py
# Purpose: Service module handling Google Calendar event creation and verification for Learning Plans.
#
# Architecture:
# React → FastAPI endpoint (/api/plan/create-calendar) → google_calendar service → Google Calendar API v3
# Sequence per day: create (events.insert) → verify (events.get) → record outcome
# ==============================================================================

import os
import datetime
from typing import Dict, Any, List
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.services.oauth import get_stored_credentials, is_google_connected
from app.schemas import LearningPlan, DayPlan


def _get_authenticated_credentials() -> Credentials:
    """
    Retrieves and refreshes stored Google OAuth credentials from server memory.

    Raises:
        ValueError: If Google account is not connected or credentials are missing/expired.
    """
    if not is_google_connected():
        raise ValueError(
            "Google account is not connected. Please connect your Google account before scheduling events."
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


def _format_event_description(day: DayPlan) -> str:
    """
    Formats objective milestones, tasks, and estimated hours into plain text for calendar event descriptions.
    """
    lines = []
    lines.append("Objectives:")
    if day.objectives:
        for obj in day.objectives:
            lines.append(f"- {obj}")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("Tasks:")
    if day.tasks:
        for task in day.tasks:
            lines.append(f"- {task}")
    else:
        lines.append("- None")

    lines.append("")
    lines.append(f"Estimated time: {day.estimatedHours} hours")
    return "\n".join(lines)


def verify_calendar_event(event_id: str) -> Dict[str, Any]:
    """
    Reusable verification function that calls Google Calendar API events().get(calendarId="primary", eventId=event_id)
    to check if an event exists and is accessible.

    Args:
        event_id: Unique Google Calendar event ID string.

    Returns:
        Dict containing:
        - "verified": bool
        - "event_id": str
        - "summary": str
        - "error": Optional[str]
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
        creds = _get_authenticated_credentials()
        calendar_service = build("calendar", "v3", credentials=creds)

        # Call events().get(calendarId="primary", eventId=...)
        event = calendar_service.events().get(calendarId="primary", eventId=cleaned_id).execute()

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
        print(f"\n[GOOGLE CALENDAR VERIFY HTTP ERROR] Event {cleaned_id}: HTTP {status_code} - {reason}")
        if hasattr(http_err, "content"):
            print(f"  Content: {getattr(http_err, 'content', None)}")
        return {
            "verified": False,
            "event_id": cleaned_id,
            "summary": "",
            "error": f"Google Calendar API verification error (HTTP {status_code}): {reason}",
        }
    except Exception as exc:
        print(f"\n[GOOGLE CALENDAR VERIFY EXCEPTION] Event {cleaned_id}: {type(exc).__name__}: {str(exc)}")
        return {
            "verified": False,
            "event_id": cleaned_id,
            "summary": "",
            "error": f"Failed to verify Google Calendar event accessibility: {str(exc)}",
        }


def create_calendar_events_for_plan(plan: LearningPlan) -> Dict[str, Any]:
    """
    Creates Google Calendar events for each learning-plan day and verifies each event.
    Distinguishes created + verified, created but unverified, and failed to create.

    Args:
        plan: Approved LearningPlan object.

    Returns:
        Dict containing:
        - "status": "success" | "partial_success" | "failure"
        - "events_count": int (total target days)
        - "created_count": int
        - "verified_count": int
        - "failed_count": int
        - "event_ids": List[str]
        - "events": List[Dict] (per-day metadata)

    Raises:
        ValueError: If Google account is not connected or plan structure is invalid.
        RuntimeError: If API client fails to initialize.
    """
    if not plan or not plan.days:
        raise ValueError("Cannot schedule an empty or invalid learning plan.")

    # 1. Retrieve authenticated credentials
    creds = _get_authenticated_credentials()

    # 2. Get local timezone configuration from environment variable
    timezone_str = os.getenv("GOOGLE_CALENDAR_TIMEZONE", "Asia/Kolkata").strip() or "Asia/Kolkata"

    # 3. Build Google Calendar API v3 client
    try:
        calendar_service = build("calendar", "v3", credentials=creds)
    except Exception as exc:
        raise RuntimeError(f"Failed to initialize Google Calendar API client: {str(exc)}")

    processed_events: List[Dict[str, Any]] = []
    created_count = 0
    verified_count = 0
    failed_count = 0

    # 4. Iterate over days and attempt creation + verification per day
    for day in plan.days:
        start_dt = datetime.datetime.combine(day.date, datetime.time(9, 0, 0))
        hours = float(day.estimatedHours) if day.estimatedHours > 0 else 1.0
        end_dt = start_dt + datetime.timedelta(hours=hours)

        max_end_dt = datetime.datetime.combine(day.date, datetime.time(23, 59, 59))
        if end_dt > max_end_dt:
            end_dt = max_end_dt

        event_body = {
            "summary": f"Day {day.day} — {day.topic}",
            "description": _format_event_description(day),
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": timezone_str,
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": timezone_str,
            },
        }

        try:
            event_res = (
                calendar_service.events()
                .insert(calendarId="primary", body=event_body)
                .execute()
            )

            event_id = event_res.get("id", "")
            created_count += 1

            # Verification step using verify_calendar_event()
            verification_res = verify_calendar_event(event_id)

            if verification_res["verified"]:
                verified_count += 1
                processed_events.append({
                    "day": day.day,
                    "topic": day.topic,
                    "date": str(day.date),
                    "eventId": event_id,
                    "htmlLink": event_res.get("htmlLink", ""),
                    "created": True,
                    "verified": True,
                    "error": None,
                })
            else:
                failed_count += 1
                processed_events.append({
                    "day": day.day,
                    "topic": day.topic,
                    "date": str(day.date),
                    "eventId": event_id,
                    "htmlLink": event_res.get("htmlLink", ""),
                    "created": True,
                    "verified": False,
                    "error": verification_res.get("error") or "Event created but verification failed.",
                })

        except HttpError as http_err:
            reason = http_err.reason if hasattr(http_err, "reason") else str(http_err)
            status_code = http_err.resp.status if hasattr(http_err, "resp") else 500
            print(f"\n[GOOGLE CALENDAR INSERT HTTP ERROR] Day {day.day}: HTTP {status_code} - {reason}")
            if hasattr(http_err, "content"):
                print(f"  Content: {getattr(http_err, 'content', None)}")
            failed_count += 1
            processed_events.append({
                "day": day.day,
                "topic": day.topic,
                "date": str(day.date),
                "eventId": None,
                "htmlLink": None,
                "created": False,
                "verified": False,
                "error": f"Creation failed (HTTP {status_code}): {reason}",
            })
        except Exception as exc:
            print(f"\n[GOOGLE CALENDAR INSERT EXCEPTION] Day {day.day}: {type(exc).__name__}: {str(exc)}")
            failed_count += 1
            processed_events.append({
                "day": day.day,
                "topic": day.topic,
                "date": str(day.date),
                "eventId": None,
                "htmlLink": None,
                "created": False,
                "verified": False,
                "error": f"Creation failed: {str(exc)}",
            })

    total_days = len(plan.days)

    if verified_count == total_days:
        status_str = "success"
    elif verified_count > 0:
        status_str = "partial_success"
    else:
        status_str = "failure"

    return {
        "status": status_str,
        "events_count": total_days,
        "created_count": created_count,
        "verified_count": verified_count,
        "failed_count": failed_count,
        "event_ids": [e["eventId"] for e in processed_events if e.get("eventId") and e.get("verified")],
        "events": processed_events,
    }
