# ==============================================================================
# File: server/app/api/v1/research.py
# Purpose: API router for web search and LangGraph topic research workflows.
# ==============================================================================

import logging
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.plan import SearchResponse, ResearchRequest, ResearchResponse
from app.services.search import search_web
from app.services.research_graph import run_research_workflow

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Research"])


@router.get(
    "/search",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search Web for Learning Resources (Tavily)",
)
def api_search_web(
    q: str = Query(..., min_length=1, description="Search query string")
) -> SearchResponse:
    """
    Executes a web search for educational resources using our search service.
    
    Flow:
    [ GET /api/search?q=... ]
             │
             ▼
    [ Validate non-empty query ]
             │
             ▼
    [ search_web() normalizes results into SearchResult ]
             │
             ▼
    [ Return SearchResponse ]
    """
    cleaned_query = q.strip()
    if not cleaned_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query 'q' cannot be empty or contain only whitespace.",
        )

    try:
        results = search_web(cleaned_query)
        return SearchResponse(
            query=cleaned_query,
            results=results,
        )
    except ValueError as val_err:
        # Handles missing TAVILY_API_KEY or query validation issues
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except RuntimeError as run_err:
        # Handles Tavily API or network errors
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Search Provider Error: {str(run_err)}",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while executing the search.",
        )


@router.post(
    "/research",
    response_model=ResearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Research Topic with LangGraph StateGraph Workflow",
)
def api_research_topic(request: ResearchRequest) -> ResearchResponse:
    """
    Executes the LangGraph research workflow.

    Flow:
    START
      ↓
    analyze_goal (LLM analysis of user topic)
      ↓
    search_resources (Deterministic Python web search via Tavily)
      ↓
    generate_response (LLM answer synthesis)
      ↓
    END
    """
    try:
        return run_research_workflow(request.query)
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
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during LangGraph workflow execution.",
        )

