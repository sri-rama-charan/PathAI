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

from typing import List, Optional
import datetime
from fastapi import FastAPI, HTTPException, Query, Request, Response, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session

from app.database import get_db, init_db
from app.models import LearningPlanModel
from app.schemas import (
    PlanRequest,
    PlanResponse,
    PlanModifyRequest,
    LearningPlan,
    SearchResponse,
    ResearchRequest,
    ResearchResponse,
    DocCreateRequest,
    DocCreateResponse,
    CalendarCreateRequest,
    CalendarCreateResponse,
    CalendarEventMeta,
    SavedPlanSummary,
    SavedPlanDetail,
    PlanPatchRequest,
)
from app.services.llm import generate_learning_plan, modify_learning_plan
from app.services.search import search_web
from app.services.research_graph import run_research_workflow
# Preserved for educational comparison between manual tool-calling and LangGraph
from app.services.tool_runner import research_topic
from app.services.oauth import (
    get_authorization_url,
    exchange_code_for_tokens,
    is_google_connected,
)
from app.services.google_docs import create_google_doc_for_plan
from app.services.google_calendar import create_calendar_events_for_plan

from contextlib import asynccontextmanager
import logging
import os



# Configure application logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

REQUIRED_PRODUCTION_VARS = [
    "GEMINI_API_KEY",
    "TAVILY_API_KEY",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_REDIRECT_URI",
    "FRONTEND_URL",
]

PLACEHOLDER_PREFIXES = [
    "your_",
    "tvly-your",
]


def validate_production_environment() -> None:
    """
    Validates required environment variables when running in production mode (ENVIRONMENT=production).
    Raises RuntimeError listing only the missing variable NAMES if any are missing or set to placeholders.
    Never logs or exposes actual variable values.
    """
    env_name = os.getenv("ENVIRONMENT", "").strip().lower()
    if env_name != "production":
        return

    missing_vars = []
    for var_name in REQUIRED_PRODUCTION_VARS:
        val = os.getenv(var_name, "").strip()
        if not val or any(val.startswith(ph) for ph in PLACEHOLDER_PREFIXES):
            missing_vars.append(var_name)

    if missing_vars:
        error_msg = f"Production startup failed: Missing or invalid required environment variable(s): {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    logger.info("Production environment validation successful. All required configuration variables are set.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup validation, database initialization,
    and shutdown lifecycle hooks.
    """
    validate_production_environment()
    try:
        init_db()
    except Exception as exc:
        logger.warning("Could not auto-initialize database on startup: %s", exc)
    yield


def get_cors_origins() -> list:
    """
    Parses CORS allowed origins from CORS_ALLOWED_ORIGINS environment variable.
    Format: comma-separated list of origin URLs.
    
    If CORS_ALLOWED_ORIGINS is missing or empty, defaults safely to development origins:
    ["http://localhost:5173", "http://127.0.0.1:5173"].
    
    Ensures wildcard '*' is never automatically included.
    """
    raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
    if raw_origins:
        parsed = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
        if parsed:
            return parsed
            
    return ["http://localhost:5173", "http://127.0.0.1:5173"]


def get_frontend_url() -> str:
    """
    Retrieves the frontend web application URL for post-OAuth redirects.
    Defaults to http://localhost:5173 if FRONTEND_URL is not configured.
    """
    return os.getenv("FRONTEND_URL", "http://localhost:5173").strip() or "http://localhost:5173"


# ------------------------------------------------------------------------------
# 1. Create the FastAPI Application
# ------------------------------------------------------------------------------
app = FastAPI(
    title="PathAI Backend",
    description="Backend API for PathAI — AI Learning Path Generator",
    version="0.3.0",
    lifespan=lifespan,
)


# ------------------------------------------------------------------------------
# 2. Security Headers Middleware
# ------------------------------------------------------------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Attaches security headers to every HTTP response:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - Referrer-Policy: strict-origin-when-cross-origin
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app.add_middleware(SecurityHeadersMiddleware)

# ------------------------------------------------------------------------------
# 3. Configure CORS (Cross-Origin Resource Sharing)
# ------------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------------------
# 4. Global Production Exception Handler
# ------------------------------------------------------------------------------
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled exceptions.
    In production (ENVIRONMENT=production), returns a generic 500 error response
    without leaking internal stack traces or implementation details to clients.
    In development mode, re-raises to preserve standard debugging behavior.
    """
    env_name = os.getenv("ENVIRONMENT", "").strip().lower()
    if env_name == "production":
        logger.error("[PRODUCTION UNHANDLED EXCEPTION] Path: %s | Error: %s", request.url.path, exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected internal server error occurred."},
        )

    raise exc

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
def submit_plan_request(
    request: PlanRequest,
    db: Session = Depends(get_db),
) -> PlanResponse:
    """
    Receives the user's learning goal and constraints, invokes Google Gemini
    to assess schedule feasibility, and generates a structured curriculum.
    Automatically saves valid, feasible plans to PostgreSQL.
    """
    try:
        plan_result = generate_learning_plan(request)
        
        saved_id: Optional[int] = None
        # Auto-save feasible, validated plans into PostgreSQL
        if plan_result.feasible and plan_result.plan:
            try:
                record = LearningPlanModel(
                    title=plan_result.plan.title,
                    goal=request.goal,
                    input_data=request.model_dump(mode="json"),
                    plan_data=plan_result.plan.model_dump(mode="json"),
                )
                db.add(record)
                db.commit()
                db.refresh(record)
                saved_id = record.id
                logger.info("Automatically saved generated plan to database with ID: %s", saved_id)
            except Exception as db_exc:
                db.rollback()
                logger.error("Failed to persist generated plan to database: %s", db_exc)

        message = (
            "Learning plan generated successfully"
            if plan_result.feasible
            else "Learning plan feasibility assessment completed"
        )
        
        return PlanResponse(
            message=message,
            data=plan_result,
            plan_id=saved_id,
            planId=saved_id,
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


# ------------------------------------------------------------------------------
# 4. My Plans Dashboard & Persistence Endpoints
# ------------------------------------------------------------------------------

@app.get(
    "/api/plans",
    response_model=List[SavedPlanSummary],
    status_code=status.HTTP_200_OK,
    summary="Retrieve all saved learning plans (newest first)",
)
def get_all_plans(db: Session = Depends(get_db)) -> List[SavedPlanSummary]:
    """
    Retrieves all saved learning plans ordered by creation date descending (newest first).
    """
    try:
        records = (
            db.query(LearningPlanModel)
            .order_by(LearningPlanModel.created_at.desc())
            .all()
        )
        return [SavedPlanSummary(**r.to_summary_dict()) for r in records]
    except Exception as exc:
        logger.error("Database error fetching plans: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while retrieving saved learning plans.",
        )


@app.get(
    "/api/plans/{plan_id}",
    response_model=SavedPlanDetail,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a specific learning plan by ID",
)
def get_plan_by_id(plan_id: int, db: Session = Depends(get_db)) -> SavedPlanDetail:
    """
    Retrieves one learning plan with full details by primary key ID.
    Raises 404 if the record does not exist.
    """
    try:
        record = (
            db.query(LearningPlanModel)
            .filter(LearningPlanModel.id == plan_id)
            .first()
        )
    except Exception as exc:
        logger.error("Database error looking up plan %s: %s", plan_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while retrieving plan details.",
        )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Learning plan with ID {plan_id} not found.",
        )

    return SavedPlanDetail(**record.to_detail_dict())


@app.patch(
    "/api/plans/{plan_id}",
    response_model=PlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Modify and update an existing learning plan in-place",
)
def patch_plan_by_id(
    plan_id: int,
    patch_req: PlanPatchRequest,
    db: Session = Depends(get_db),
) -> PlanResponse:
    """
    Modifies an existing plan record in-place based on user feedback.
    Reuses existing modify_learning_plan and validation logic.
    Updates the database record rather than creating a duplicate.
    """
    try:
        record = (
            db.query(LearningPlanModel)
            .filter(LearningPlanModel.id == plan_id)
            .first()
        )
    except Exception as exc:
        logger.error("Database error looking up plan %s for modification: %s", plan_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while accessing plan for modification.",
        )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Learning plan with ID {plan_id} not found.",
        )

    # Reconstruct currentPlan and schedule constraints
    current_plan_data = patch_req.currentPlan or LearningPlan(**record.plan_data)
    input_data = record.input_data if isinstance(record.input_data, dict) else {}
    duration_days = (
        patch_req.durationDays
        or input_data.get("durationDays")
        or len(current_plan_data.days)
    )
    hours_per_day = (
        patch_req.hoursPerDay
        or input_data.get("hoursPerDay")
        or (current_plan_data.days[0].estimatedHours if current_plan_data.days else 2.0)
    )
    start_date_val = patch_req.startDate
    if not start_date_val:
        raw_start = input_data.get("startDate")
        if raw_start:
            if isinstance(raw_start, str):
                start_date_val = datetime.date.fromisoformat(raw_start)
            elif isinstance(raw_start, datetime.date):
                start_date_val = raw_start
        elif current_plan_data.days:
            start_date_val = current_plan_data.days[0].date
        else:
            start_date_val = datetime.date.today()

    modify_request = PlanModifyRequest(
        currentPlan=current_plan_data,
        feedback=patch_req.feedback,
        durationDays=duration_days,
        hoursPerDay=hours_per_day,
        startDate=start_date_val,
    )

    try:
        plan_result = modify_learning_plan(modify_request)
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

    # Update the existing database record in-place
    if plan_result.plan:
        try:
            record.title = plan_result.plan.title
            record.plan_data = plan_result.plan.model_dump(mode="json")
            if isinstance(record.input_data, dict):
                updated_input = dict(record.input_data)
                updated_input["durationDays"] = duration_days
                updated_input["hoursPerDay"] = hours_per_day
                updated_input["startDate"] = str(start_date_val)
                record.input_data = updated_input
            db.commit()
            db.refresh(record)
            logger.info("Successfully updated existing plan record ID %s in-place", plan_id)
        except Exception as db_exc:
            db.rollback()
            logger.error("Failed to update plan record %s in database: %s", plan_id, db_exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error while saving modified plan.",
            )

    return PlanResponse(
        message="Learning plan modified and updated successfully",
        data=plan_result,
        plan_id=record.id,
        planId=record.id,
    )


# ------------------------------------------------------------------------------
# 4. Google OAuth Endpoints
# ------------------------------------------------------------------------------

@app.get(
    "/api/auth/google",
    summary="Initiate Google OAuth Flow",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
)
def initiate_google_oauth():
    """
    Redirects user to Google OAuth 2.0 authorization page.
    Checks environment variables and handles missing config errors.
    """
    try:
        auth_url, _ = get_authorization_url()
        return RedirectResponse(url=auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(val_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate Google OAuth flow: {str(exc)}",
        )


@app.get(
    "/api/auth/google/callback",
    summary="Google OAuth Callback Handler",
)
def google_oauth_callback(
    code: Optional[str] = Query(None, description="Authorization code returned by Google"),
    error: Optional[str] = Query(None, description="OAuth error code returned by Google"),
    state: Optional[str] = Query(None, description="State verification token"),
):
    """
    Handles redirect from Google OAuth authorization page:
    - Receives authorization code
    - Exchanges code for access/refresh tokens
    - Handles OAuth denial and token exchange errors safely
    - Temporarily stores credentials in server memory for this dev phase
    - Redirects back to frontend UI with status
    """
    frontend_url = get_frontend_url()

    # 1. Handle OAuth denial or error returned by Google
    if error:
        return RedirectResponse(
            url=f"{frontend_url}/?auth_error={error}",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )

    # 2. Handle missing authorization code or state token
    if not code or not state:
        return RedirectResponse(
            url=f"{frontend_url}/?auth_error=missing_code",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )

    # 3. Exchange code for tokens & store in server memory
    try:
        exchange_code_for_tokens(code, state=state)
        return RedirectResponse(
            url=f"{frontend_url}/?auth=success",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
    except Exception as exc:
        print(f"[OAUTH CALLBACK ERROR] Token exchange failed: {exc}")
        return RedirectResponse(
            url=f"{frontend_url}/?auth_error=token_exchange_failed",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )


@app.get(
    "/api/auth/status",
    summary="Check Google Auth Status",
)
def check_auth_status():
    """
    Returns whether Google account credentials are connected in server memory.
    """
    return {"connected": is_google_connected()}


# ------------------------------------------------------------------------------
# 5. Google Docs Creation Endpoint
# ------------------------------------------------------------------------------

@app.post(
    "/api/plan/create-doc",
    response_model=DocCreateResponse,
    status_code=status.HTTP_200_OK,
    summary="Create Google Doc for Approved Learning Plan",
)
def api_create_google_doc(
    request: DocCreateRequest,
    db: Session = Depends(get_db),
) -> DocCreateResponse:
    """
    Receives an approved LearningPlan and creates a formatted Google Doc.
    If request.plan_id is provided, automatically saves the document URL against the database record.
    """
    # 1. Reject if Google account is not connected
    if not is_google_connected():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account is not connected. Please connect your Google account before creating a Google Doc.",
        )

    # 2. Invoke Google Docs creation service module
    try:
        result = create_google_doc_for_plan(request.plan)
        doc_url = result.get("document_url")

        # Save Google Docs URL against plan record if plan_id is provided
        if request.plan_id and doc_url:
            try:
                db_record = db.query(LearningPlanModel).filter(LearningPlanModel.id == request.plan_id).first()
                if db_record:
                    db_record.google_doc_url = doc_url
                    db.commit()
                    logger.info("Saved Google Doc URL against plan ID %s", request.plan_id)
            except Exception as db_err:
                db.rollback()
                logger.error("Failed to associate Google Doc URL with plan ID %s: %s", request.plan_id, db_err)

        if not result["verified"]:
            return DocCreateResponse(
                message=result.get("error") or f"Google Doc was created ({result['document_id']}), but PathAI could not verify it.",
                documentId=result["document_id"],
                documentUrl=result["document_url"],
                verified=False,
            )

        return DocCreateResponse(
            message="Google Doc created and verified successfully",
            documentId=result["document_id"],
            documentUrl=result["document_url"],
            verified=True,
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
            detail=f"An unexpected error occurred while creating the Google Doc: {str(exc)}",
        )


# ------------------------------------------------------------------------------
# 6. Google Calendar Event Scheduling Endpoint
# ------------------------------------------------------------------------------

@app.post(
    "/api/plan/create-calendar",
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
