# ==============================================================================
# File: server/app/services/google_docs.py
# Purpose: Service module handling Google Docs creation and verification for Learning Plans.
#
# Architecture:
# React → FastAPI endpoint (/api/plan/create-doc) → google_docs service → Google Docs API
# Flow: create → insert content → verify (documents.get) → return result
# ==============================================================================

from typing import Dict, Any, Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.services.oauth import get_stored_credentials, is_google_connected
from app.schemas import LearningPlan


def _get_authenticated_credentials() -> Credentials:
    """
    Retrieves and refreshes stored Google OAuth credentials from server memory.

    Raises:
        ValueError: If Google account is not connected or token is invalid/expired.
    """
    if not is_google_connected():
        raise ValueError(
            "Google account is not connected. Please connect your Google account before accessing Google Docs."
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


def format_plan_as_text(plan: LearningPlan) -> str:
    """
    Formats an approved LearningPlan into plain text following the required structure:
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
    Reusable verification function that checks if a Google Doc exists and is accessible
    via the Google Docs API documents().get(documentId=...) method.

    Args:
        document_id: Unique Google Docs document ID string.

    Returns:
        Dict containing:
        - "verified": bool
        - "document_id": str
        - "title": str
        - "error": Optional[str]
    """
    cleaned_id = document_id.strip() if document_id else ""
    if not cleaned_id:
        return {
            "verified": False,
            "document_id": "",
            "title": "",
            "error": "Document ID cannot be empty for verification.",
        }

    try:
        creds = _get_authenticated_credentials()
        docs_service = build("docs", "v1", credentials=creds)

        # Call documents.get(documentId=...) API
        doc = docs_service.documents().get(documentId=cleaned_id).execute()

        retrieved_id = doc.get("documentId", cleaned_id)
        doc_title = doc.get("title", "")

        if retrieved_id == cleaned_id:
            return {
                "verified": True,
                "document_id": retrieved_id,
                "title": doc_title,
                "error": None,
            }
        else:
            return {
                "verified": False,
                "document_id": cleaned_id,
                "title": doc_title,
                "error": "Document ID mismatch during verification.",
            }

    except HttpError as http_err:
        reason = http_err.reason if hasattr(http_err, "reason") else str(http_err)
        status_code = http_err.resp.status if hasattr(http_err, "resp") else 500
        return {
            "verified": False,
            "document_id": cleaned_id,
            "title": "",
            "error": f"Google Docs API verification error (HTTP {status_code}): {reason}",
        }
    except Exception as exc:
        return {
            "verified": False,
            "document_id": cleaned_id,
            "title": "",
            "error": f"Failed to verify Google Doc accessibility: {str(exc)}",
        }


def create_google_doc_for_plan(plan: LearningPlan) -> Dict[str, Any]:
    """
    Executes Google Doc creation flow:
      1. create (documents.create)
      2. insert content (documents.batchUpdate)
      3. verify (verify_google_doc via documents.get)

    Args:
        plan: Approved LearningPlan object.

    Returns:
        Dict containing document_id, document_url, verified status, and optional error detail.

    Raises:
        ValueError: If Google account is not connected or credentials expired.
        RuntimeError: If document creation or initial batchUpdate fails.
    """
    # 1. Retrieve authenticated credentials
    creds = _get_authenticated_credentials()

    # 2. Create blank doc and insert content
    try:
        docs_service = build("docs", "v1", credentials=creds)

        doc_title = plan.title.strip() if plan.title else "PathAI Learning Plan"
        doc = docs_service.documents().create(body={"title": doc_title}).execute()
        document_id = doc.get("documentId")

        if not document_id:
            raise RuntimeError("Google Docs API created document but returned empty documentId.")

        document_url = f"https://docs.google.com/document/d/{document_id}/edit"

        content_text = format_plan_as_text(plan)
        requests = [
            {
                "insertText": {
                    "location": {"index": 1},
                    "text": content_text,
                }
            }
        ]

        docs_service.documents().batchUpdate(
            documentId=document_id,
            body={"requests": requests},
        ).execute()

    except HttpError as http_err:
        reason = http_err.reason if hasattr(http_err, "reason") else str(http_err)
        status_code = http_err.resp.status if hasattr(http_err, "resp") else 500
        raise RuntimeError(f"Google Docs API error (HTTP {status_code}): {reason}")
    except Exception as exc:
        raise RuntimeError(f"Failed to create Google Doc: {str(exc)}")

    # 3. Verify the document actually exists and is accessible
    verification_res = verify_google_doc(document_id)

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
