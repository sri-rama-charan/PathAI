# ==============================================================================
# File: server/app/services/calendar_service.py
# Purpose: Google Calendar scheduling business logic for Learning Plans.
#
# Responsibilities:
#   - Coordinate Google OAuth credential retrieval.
#   - Format calendar event bodies from learning-plan day data.
#   - Delegate actual API calls to app.integrations.google_calendar.
#   - Aggregate per-event creation and verification results.
# ==============================================================================

import datetime
import os
from typing import Any, Dict, List

from app.integrations.google_calendar import insert_event, verify_event
from app.integrations.google_oauth import get_authenticated_credentials
from app.schemas.plan import DayPlan, LearningPlan


def _format_event_description(day: DayPlan) -> str:
    """
    Formats objective milestones, tasks, and estimated hours into plain text
    for calendar event descriptions.
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


def create_calendar_events_for_plan(plan: LearningPlan) -> Dict[str, Any]:
    """
    Creates Google Calendar events for each learning-plan day and verifies each event.
    Distinguishes created + verified, created but unverified, and failed to create.

    Returns:
        Dict containing status, counts, event IDs, and per-day metadata.
    """
    if not plan or not plan.days:
        raise ValueError("Cannot schedule an empty or invalid learning plan.")

    creds = get_authenticated_credentials()
    timezone_str = os.getenv("GOOGLE_CALENDAR_TIMEZONE", "Asia/Kolkata").strip() or "Asia/Kolkata"

    processed_events: List[Dict[str, Any]] = []
    created_count = 0
    verified_count = 0
    failed_count = 0

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
            event_res = insert_event(event_body=event_body, credentials=creds)
            event_id = event_res.get("id", "")
            created_count += 1

            verification_res = verify_event(event_id=event_id, credentials=creds)

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

        except Exception as exc:
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

