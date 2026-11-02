# ==============================================================================
# File: server/app/integrations/google_docs.py
# Purpose: Google Docs API v1 communication and document verification.
# ==============================================================================

from typing import Dict, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def create_document(title: str, content: str, credentials: Any) -> Dict[str, Any]:
    """
    Creates a new Google Doc and inserts content via Google Docs API v1.
    
    Args:
        title: Title of the Google Doc.
        content: Text content to insert into the document.
        credentials: Authenticated Google Credentials instance.
        
    Returns:
        Dict[str, Any]: Contains 'document_id' and 'document_url'.
        
    Raises:
        RuntimeError: If document creation or content insertion fails.
    """
    try:
        docs_service = build("docs", "v1", credentials=credentials)
        doc_title = title.strip() if title else "PathAI Learning Plan"
        doc = docs_service.documents().create(body={"title": doc_title}).execute()
        document_id = doc.get("documentId")

        if not document_id:
            raise RuntimeError("Google Docs API created document but returned empty documentId.")

        document_url = f"https://docs.google.com/document/d/{document_id}/edit"

        if content:
            requests = [
                {
                    "insertText": {
                        "location": {"index": 1},
                        "text": content,
                    }
                }
            ]
            docs_service.documents().batchUpdate(
                documentId=document_id,
                body={"requests": requests},
            ).execute()

        return {
            "document_id": document_id,
            "document_url": document_url,
            "title": doc_title,
        }

    except HttpError as http_err:
        reason = http_err.reason if hasattr(http_err, "reason") else str(http_err)
        status_code = http_err.resp.status if hasattr(http_err, "resp") else 500
        raise RuntimeError(f"Google Docs API error (HTTP {status_code}): {reason}") from http_err
    except Exception as exc:
        raise RuntimeError(f"Failed to create Google Doc: {str(exc)}") from exc


def verify_document(document_id: str, credentials: Any) -> Dict[str, Any]:
    """
    Verifies that a Google Doc exists and is accessible via documents().get().
    
    Args:
        document_id: Unique Google Docs document ID string.
        credentials: Authenticated Google Credentials instance.
        
    Returns:
        Dict[str, Any]: Contains 'verified', 'document_id', 'title', and optional 'error'.
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
        docs_service = build("docs", "v1", credentials=credentials)
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

