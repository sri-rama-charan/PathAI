# ==============================================================================
# File: server/tests/test_agent_retry.py
# Purpose: Evaluation test verifying LangGraph research workflow retry loop behavior.
# ==============================================================================

from unittest.mock import MagicMock, patch
import pytest

from app.schemas import SearchResult
from app.services.research_graph import build_research_graph, ResearchState


def test_research_graph_retry_loop():
    """
    Tests that the LangGraph research workflow performs a search retry when initial
    results are insufficient, uses the refined query on the retry, and completes after
    results become sufficient.
    """
    # 1. Mock analyze_goal node: returns initial analysis & search query
    def mock_analyze_goal(state: ResearchState) -> dict:
        return {
            "analysis": "Initial analysis of React learning goal.",
            "search_query": "React beginner tutorials",
        }

    # 2. Mock search_web: 1st call returns poor results, 2nd call returns useful results
    poor_result = SearchResult(
        title="Poor Result",
        url="https://example.com/poor",
        description="Vague or insufficient information.",
        source="example.com",
    )
    good_result = SearchResult(
        title="React Beginner Hands-On Guide",
        url="https://example.com/react-hands-on",
        description="Comprehensive hands-on React project tutorial.",
        source="example.com",
    )

    mock_search_web = MagicMock()
    mock_search_web.side_effect = [
        [poor_result],
        [good_result],
    ]

    # 3. Mock evaluate_resources node: 1st call returns insufficient, 2nd call returns sufficient
    mock_evaluate_resources = MagicMock()
    mock_evaluate_resources.side_effect = [
        {
            "evaluation": {
                "sufficient": False,
                "reason": "Missing beginner React hands-on resources",
                "missing_information": ["beginner React hands-on resources"],
                "better_search_query": "React beginner hands-on projects tutorial",
            },
            "search_query": "React beginner hands-on projects tutorial",
        },
        {
            "evaluation": {
                "sufficient": True,
                "reason": "Retrieved high quality hands-on React resources.",
                "better_search_query": "",
            },
        },
    ]

    # 4. Mock generate_response node: returns final answer
    def mock_generate_response(state: ResearchState) -> dict:
        return {
            "final_answer": "Complete structured React curriculum and resources roadmap.",
        }

    # Patch the graph node implementations before compiling the workflow
    with patch("app.workflows.research_graph.analyze_goal", side_effect=mock_analyze_goal), \
         patch("app.workflows.research_graph.search_web", mock_search_web), \
         patch("app.workflows.research_graph.evaluate_resources", mock_evaluate_resources), \
         patch("app.workflows.research_graph.generate_response", side_effect=mock_generate_response):

        graph = build_research_graph()

        initial_state: ResearchState = {
            "run_id": "test_run_retry",
            "user_query": "Learn React",
            "analysis": None,
            "search_query": None,
            "search_results": [],
            "evaluation": None,
            "retry_count": 0,
            "final_answer": None,
        }

        # Act: Execute compiled LangGraph workflow
        final_state = graph.invoke(initial_state)

        # Assert 1: search_web was called exactly twice (no third search occurred)
        assert mock_search_web.call_count == 2

        # Assert 2: Second search used the improved query from 1st evaluation
        first_search_query = mock_search_web.call_args_list[0].kwargs.get("query")
        second_search_query = mock_search_web.call_args_list[1].kwargs.get("query")
        assert first_search_query == "React beginner tutorials"
        assert second_search_query == "React beginner hands-on projects tutorial"

        # Assert 3: evaluate_resources was called twice
        assert mock_evaluate_resources.call_count == 2

        # Assert 4: retry_count in state reflects that a retry occurred (retry_count == 2)
        assert final_state.get("retry_count") == 2

        # Assert 5: Workflow reached generate_response and completed successfully
        assert final_state.get("final_answer") == "Complete structured React curriculum and resources roadmap."

        # Assert 6: Returned search results match final state
        assert len(final_state.get("search_results", [])) == 1
        assert final_state["search_results"][0].title == "React Beginner Hands-On Guide"
