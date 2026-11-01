# ==============================================================================
# File: server/tests/test_agent_failures.py
# Purpose: Evaluation test for external search failure handling (Tavily/search_web).
# ==============================================================================

from unittest.mock import MagicMock, patch
import pytest

from app.schemas import ResearchResponse
from app.services.research_graph import run_research_workflow, MAX_RETRIES


def mock_evaluate_resources_for_failure(state):
    return {
        "evaluation": {
            "sufficient": False,
            "reason": "Search failed or returned no results.",
            "better_search_query": "React beginner documentation",
        }
    }


def mock_generate_response_for_failure(state):
    return {
        "final_answer": "No web resources could be retrieved due to external search provider failure."
    }


def test_research_workflow_external_search_failure():
    """
    Evaluation test verifying how the research workflow handles external search_web failures.
    Simulates Tavily/search_web raising a RuntimeError exception.
    """
    mock_search_web = MagicMock()
    mock_search_web.side_effect = RuntimeError("Tavily Search API Connection Timeout")
    mock_call_gemini = MagicMock(return_value="Analysis: React fundamentals. Search Query: Learn React tutorials documentation")

    with patch("app.services.research_graph._generate_with_fallback", mock_call_gemini), \
         patch("app.services.research_graph.search_web", mock_search_web), \
         patch("app.services.research_graph.evaluate_resources", side_effect=mock_evaluate_resources_for_failure), \
         patch("app.services.research_graph.generate_response", side_effect=mock_generate_response_for_failure):

        # Act: Execute research workflow with failing search_web
        response = run_research_workflow("Learn React")

        # Verify 1: Workflow completed safely returning ResearchResponse
        assert isinstance(response, ResearchResponse)

        # Verify 2: Does not claim useful resources were found (sources is empty)
        assert isinstance(response.sources, list)
        assert len(response.sources) == 0

        # Verify 3: search_web call count does not exceed retries limit
        assert mock_search_web.call_count <= MAX_RETRIES + 1

        # Verify 4: Final answer is inspectable and reflects output state
        assert isinstance(response.answer, str)
        assert len(response.answer) > 0
