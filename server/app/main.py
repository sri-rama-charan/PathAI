# ==============================================================================
# File: server/app/main.py
# Purpose: Entry point for the PathAI FastAPI backend server.
#
# What this file does:
# 1. Creates the FastAPI application instance.
# 2. Configures CORS (Cross-Origin Resource Sharing) for local React development.
# 3. Exposes GET /: Root health check endpoint.
# 4. Exposes POST /api/plan: Calls Gemini LLM to assess feasibility and generate structured plans.
# 5. Exposes GET /api/search: Executes provider-independent web searches using Tavily.
# 6. Exposes GET /docs: Interactive Swagger UI.
# ==============================================================================

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import (
    PlanRequest,
    PlanResponse,
    PlanModifyRequest,
    SearchResponse,
    ResearchRequest,
    ResearchResponse,
)
from app.services.llm import generate_learning_plan, modify_learning_plan
from app.services.search import search_web
from app.services.research_graph import run_research_workflow
# Preserved for educational comparison between manual tool-calling and LangGraph
from app.services.tool_runner import research_topic

# ------------------------------------------------------------------------------
# 1. Create the FastAPI Application
# ------------------------------------------------------------------------------
app = FastAPI(
    title="PathAI Backend",
    description="Backend API for PathAI — AI Learning Path Generator",
    version="0.3.0",
)

# ------------------------------------------------------------------------------
# 2. Configure CORS (Cross-Origin Resource Sharing)
# ------------------------------------------------------------------------------
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------------------
# 3. Define Endpoints
# ------------------------------------------------------------------------------

@app.get("/", summary="Root Health Check")
def read_root():
    """
    Root endpoint for PathAI.
    """
    return {
        "status": "online",
        "message": "PathAI backend is running successfully!",
        "service": "PathAI",
        "docs_url": "/docs",
    }


@app.post(
    "/api/plan",
    response_model=PlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate AI Learning Plan or Feasibility Assessment",
)
def submit_plan_request(request: PlanRequest) -> PlanResponse:
    """
    Receives the user's learning goal and constraints, invokes Google Gemini
    to assess schedule feasibility, and generates a structured curriculum.
    """
    try:
        plan_result = generate_learning_plan(request)
        
        message = (
            "Learning plan generated successfully"
            if plan_result.feasible
            else "Learning plan feasibility assessment completed"
        )
        
        return PlanResponse(
            message=message,
            data=plan_result,
        )

    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except RuntimeError as run_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI Service Error: {str(run_err)}",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating the learning plan.",
        )


@app.get(
    "/api/search",
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


@app.post(
    "/api/research",
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


@app.post(
    "/api/plan/modify",
    response_model=PlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Modify an Existing AI Learning Plan Based on User Feedback",
)
def modify_plan_request(request: PlanModifyRequest) -> PlanResponse:
    """
    Receives the current learning plan and user feedback, asks Gemini to
    produce a modified version that preserves the original schedule constraints
    (duration, start date, daily hours) while applying the requested changes.

    Flow:
      POST /api/plan/modify
        ↓
      Validate PlanModifyRequest (Pydantic)
        ↓
      modify_learning_plan() → Gemini (structured output)
        ↓
      validate_modified_plan() — strict constraint checks
        ↓
      validate_and_fix_plan_deterministically() — date/day/hour corrections
        ↓
      Return PlanResponse
    """
    try:
        plan_result = modify_learning_plan(request)
        return PlanResponse(
            message="Learning plan modified successfully",
            data=plan_result,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except RuntimeError as run_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI Service Error: {str(run_err)}",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while modifying the learning plan.",
        )
