# ==============================================================================
# File: server/app/api/v1/calendar.py
# Purpose: API router for Google Calendar event scheduling endpoints.
# ==============================================================================

import logging
from fastapi import APIRouter, HTTPException, status

from app.schemas.plan import CalendarCreateRequest, CalendarCreateResponse, CalendarEventMeta
from app.services.oauth import is_google_connected
from app.services.google_calendar import create_calendar_events_for_plan

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Calendar"])


@router.post(
    "/plan/create-calendar",
    response_model=CalendarCreateResponse,
    status_code=status.HTTP_200_OK,
    summary="Schedule Learning Plan on Google Calendar",
)
def api_create_calendar_events(request: CalendarCreateRequest) -> CalendarCreateResponse:
    """
    Receives an approved LearningPlan and schedules one Google Calendar event per plan day.
    
    Checks:
    - Verifies Google account connection in server memory.
    - Validates plan payload and daily schedule.
    - Generates calendar events via google_calendar service and returns event IDs and metadata.
    """
    # 1. Reject if Google account is not connected
    if not is_google_connected():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account is not connected. Please connect your Google account before scheduling Calendar events.",
        )

    # 2. Invoke Google Calendar creation service module
    try:
        res = create_calendar_events_for_plan(request.plan)
        status_code_str = res["status"]

        if status_code_str == "success":
            message = f"✓ Learning Plan Scheduled ({res['verified_count']} of {res['events_count']} events verified)"
        elif status_code_str == "partial_success":
            message = f"⚠ Calendar scheduling partially completed ({res['verified_count']} of {res['events_count']} events verified)"
        else:
            message = f"✕ Calendar scheduling failed ({res['failed_count']} of {res['events_count']} events failed)"

        return CalendarCreateResponse(
            message=message,
            status=status_code_str,
            eventsCount=res["events_count"],
            createdCount=res["created_count"],
            verifiedCount=res["verified_count"],
            failedCount=res["failed_count"],
            eventIds=res["event_ids"],
            events=[CalendarEventMeta(**item) for item in res["events"]],
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except RuntimeError as run_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(run_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while scheduling Google Calendar events: {str(exc)}",
        )

