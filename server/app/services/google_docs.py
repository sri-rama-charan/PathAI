# ==============================================================================
# File: server/app/services/google_docs.py
# Purpose: Service module handling Google Docs curriculum formatting and export workflow.
# ==============================================================================

from typing import Dict, Any, Optional

from app.schemas.plan import LearningPlan
from app.integrations.google_oauth import get_authenticated_credentials, is_google_connected
from app.integrations.google_docs import create_document, verify_document


def format_plan_as_text(plan: LearningPlan) -> str:
    """
    Formats an approved LearningPlan into structured plain text:
    - Title
    - Overview
    - Prerequisites
    - Daily Schedule (Day, Date, Objectives, Tasks, Estimated time)
    """
    lines = []

    # Title
    lines.append(f"{plan.title}")
    lines.append("")

    # Overview
    lines.append("Overview:")
    lines.append(f"{plan.overview}")
    lines.append("")

    # Prerequisites
    lines.append("Prerequisites:")
    if plan.prerequisites:
        for prereq in plan.prerequisites:
            lines.append(f"- {prereq}")
    else:
        lines.append("- None")
    lines.append("")

    # Daily Schedule
    lines.append("Daily Schedule:")
    lines.append("")

    for day in plan.days:
        lines.append(f"Day {day.day} — {day.topic}")
        lines.append(f"Date: {day.date}")
        lines.append("Objectives:")
        if day.objectives:
            for obj in day.objectives:
                lines.append(f"- {obj}")
        else:
            lines.append("- None")

        lines.append("Tasks:")
        if day.tasks:
            for task in day.tasks:
                lines.append(f"- {task}")
        else:
            lines.append("- None")

        lines.append(f"Estimated time: {day.estimatedHours} hours")
        lines.append("")

    return "\n".join(lines)


def verify_google_doc(document_id: str) -> Dict[str, Any]:
    """
    Checks if a Google Doc exists and is accessible.
    """
    creds = get_authenticated_credentials()
    return verify_document(document_id=document_id, credentials=creds)


def create_google_doc_for_plan(plan: LearningPlan) -> Dict[str, Any]:
    """
    Executes Google Doc creation workflow:
      1. Authenticates using stored credentials.
      2. Formats curriculum as plain text.
      3. Calls Google Docs integration to create and insert content.
      4. Verifies document accessibility.

    Returns:
        Dict containing document_id, document_url, verified status, and optional error detail.
    """
    creds = get_authenticated_credentials()
    content_text = format_plan_as_text(plan)

    doc_res = create_document(
        title=plan.title,
        content=content_text,
        credentials=creds,
    )

    document_id = doc_res["document_id"]
    document_url = doc_res["document_url"]
    doc_title = doc_res.get("title", plan.title)

    # Verify the document actually exists and is accessible
    verification_res = verify_document(document_id=document_id, credentials=creds)

    if not verification_res["verified"]:
        return {
            "document_id": document_id,
            "document_url": document_url,
            "verified": False,
            "title": doc_title,
            "error": verification_res.get("error")
            or "Google Doc was created, but PathAI could not verify it.",
        }

    return {
        "document_id": document_id,
        "document_url": document_url,
        "verified": True,
        "title": verification_res.get("title") or doc_title,
        "error": None,
    }
