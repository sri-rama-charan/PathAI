# ==============================================================================
# File: server/app/workflows/states.py
# Purpose: TypedDict state definitions for LangGraph workflows.
# ==============================================================================

from typing import List, Optional, TypedDict

from app.schemas.plan import SearchResult


class ResearchState(TypedDict):
    """
    Shared state passed through every node in the research graph.

    Attributes:
        run_id        : Unique correlation ID for tracking this workflow run.
        user_query    : The original query submitted by the user.
        analysis      : Gemini's brief analysis of the user's goal.
        search_query  : The actual query string sent to Tavily (may be refined
                        by evaluate_resources on retry iterations).
        search_results: Normalised web results retrieved from Tavily.
        evaluation    : Dict produced by evaluate_resources:
                          {
                            "sufficient": bool,
                            "reason": str,
                            "better_search_query": str  # relevant when sufficient=False
                          }
        retry_count   : How many search-evaluate cycles have completed so far.
        final_answer  : Gemini's final synthesised response.
    """
    run_id: Optional[str]
    user_query: str
    analysis: Optional[str]
    search_query: Optional[str]
    search_results: List[SearchResult]
    evaluation: Optional[dict]
    retry_count: int
    final_answer: Optional[str]

