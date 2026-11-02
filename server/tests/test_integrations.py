# ==============================================================================
# File: server/tests/test_integrations.py
# Purpose: Unit tests for external integrations layer (Gemini, Tavily, Google APIs).
# ==============================================================================

import os
from unittest.mock import MagicMock, patch
import pytest

from app.integrations.gemini import get_gemini_client, generate_structured_content
from app.integrations.tavily import get_tavily_api_key, execute_tavily_search
from app.integrations.google_oauth import (
    configure_oauth_transport,
    get_oauth_config,
    get_authorization_url,
    exchange_code_for_tokens,
    is_google_connected,
    get_stored_credentials,
    clear_stored_credentials,
    get_authenticated_credentials,
)
from app.integrations.google_docs import create_document, verify_document
from app.integrations.google_calendar import insert_event, verify_event


# ------------------------------------------------------------------------------
# 1. Gemini Integration Tests
# ------------------------------------------------------------------------------
def test_get_gemini_client_missing_key():
    with patch("app.integrations.gemini.load_dotenv"), patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=True):
        with pytest.raises(ValueError, match="GEMINI_API_KEY is not set"):
            get_gemini_client()


def test_generate_structured_content_success():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"feasible": true}'
    mock_client.models.generate_content.return_value = mock_response

    result = generate_structured_content(
        client=mock_client,
        prompt="Evaluate learning goal",
        schema=dict,
        system_instruction="System prompt",
        fallback_models=["gemini-2.5-flash"],
    )
    assert result == '{"feasible": true}'


# ------------------------------------------------------------------------------
# 2. Tavily Integration Tests
# ------------------------------------------------------------------------------
def test_get_tavily_api_key_missing():
    with patch("app.integrations.tavily.load_dotenv"), patch.dict(os.environ, {"TAVILY_API_KEY": ""}, clear=True):
        with pytest.raises(ValueError, match="TAVILY_API_KEY is not set"):
            get_tavily_api_key()


def test_execute_tavily_search_empty_query():
    with pytest.raises(ValueError, match="Search query cannot be empty"):
        execute_tavily_search("")


@patch("app.integrations.tavily.TavilyClient")
@patch("app.integrations.tavily.get_tavily_api_key", return_value="tvly-mock-key")
def test_execute_tavily_search_success(mock_get_key, mock_client_cls):
    mock_client_instance = MagicMock()
    mock_client_instance.search.return_value = {
        "results": [
            {"title": "FastAPI Guide", "url": "https://fastapi.tiangolo.com", "content": "FastAPI intro"}
        ]
    }
    mock_client_cls.return_value = mock_client_instance

    results = execute_tavily_search("fastapi documentation")
    assert len(results) == 1
    assert results[0]["title"] == "FastAPI Guide"


# ------------------------------------------------------------------------------
# 3. Google OAuth Integration Tests
# ------------------------------------------------------------------------------
def test_get_oauth_config_missing_vars():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="Google OAuth configuration error"):
            get_oauth_config()


def test_is_google_connected_and_clear():
    clear_stored_credentials()
    assert is_google_connected() is False
    assert get_stored_credentials() is None


# ------------------------------------------------------------------------------
# 4. Google Docs Integration Tests
# ------------------------------------------------------------------------------
@patch("app.integrations.google_docs.build")
def test_create_document_success(mock_build):
    mock_service = MagicMock()
    mock_create = MagicMock()
    mock_create.execute.return_value = {"documentId": "doc-xyz-123"}
    mock_service.documents().create.return_value = mock_create

    mock_batch = MagicMock()
    mock_batch.execute.return_value = {}
    mock_service.documents().batchUpdate.return_value = mock_batch

    mock_build.return_value = mock_service
    mock_creds = MagicMock()

    res = create_document("Test Plan", "Content body", mock_creds)
    assert res["document_id"] == "doc-xyz-123"
    assert "https://docs.google.com/document/d/doc-xyz-123/edit" == res["document_url"]


@patch("app.integrations.google_docs.build")
def test_verify_document_success(mock_build):
    mock_service = MagicMock()
    mock_get = MagicMock()
    mock_get.execute.return_value = {"documentId": "doc-xyz-123", "title": "Verified Title"}
    mock_service.documents().get.return_value = mock_get
    mock_build.return_value = mock_service

    res = verify_document("doc-xyz-123", MagicMock())
    assert res["verified"] is True
    assert res["document_id"] == "doc-xyz-123"
    assert res["title"] == "Verified Title"


# ------------------------------------------------------------------------------
# 5. Google Calendar Integration Tests
# ------------------------------------------------------------------------------
@patch("app.integrations.google_calendar.build")
def test_insert_event_success(mock_build):
    mock_service = MagicMock()
    mock_insert = MagicMock()
    mock_insert.execute.return_value = {"id": "event-123", "htmlLink": "https://calendar.google.com/event"}
    mock_service.events().insert.return_value = mock_insert
    mock_build.return_value = mock_service

    res = insert_event({"summary": "Study Session"}, MagicMock())
    assert res["id"] == "event-123"


@patch("app.integrations.google_calendar.build")
def test_verify_event_success(mock_build):
    mock_service = MagicMock()
    mock_get = MagicMock()
    mock_get.execute.return_value = {"id": "event-123", "summary": "Study Session"}
    mock_service.events().get.return_value = mock_get
    mock_build.return_value = mock_service

    res = verify_event("event-123", MagicMock())
    assert res["verified"] is True
    assert res["event_id"] == "event-123"
