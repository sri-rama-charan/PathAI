# ==============================================================================
# File: server/app/main.py
# Purpose: Entry point for the PathAI FastAPI backend server.
#
# What this file does:
# 1. Creates the FastAPI application instance.
# 2. Configures CORS (Cross-Origin Resource Sharing) so our React frontend can call it.
# 3. Exposes GET /: Root health check confirming the server is online.
# 4. Exposes POST /api/plan: Receives and validates the learning-plan configuration.
# 5. Exposes GET /docs: Interactive Swagger UI documentation.
# ==============================================================================

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import PlanRequest, PlanResponse

# ------------------------------------------------------------------------------
# 1. Create the FastAPI Application
# ------------------------------------------------------------------------------
app = FastAPI(
    title="PathAI Backend",
    description="Backend API for PathAI — AI Learning Path Generator",
    version="0.1.0",
)

# ------------------------------------------------------------------------------
# 2. Configure CORS (Cross-Origin Resource Sharing)
# ------------------------------------------------------------------------------
# Why this is needed:
# Web browsers enforce a security policy called 'Same-Origin Policy'.
# Since our React frontend runs at http://localhost:5173 and our FastAPI backend
# runs at http://localhost:8000, CORS middleware explicitly grants permission
# for our frontend to make requests without being blocked.
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow GET, POST, PUT, DELETE, OPTIONS, etc.
    allow_headers=["*"],  # Allow all headers (Content-Type, Authorization, etc.)
)

# ------------------------------------------------------------------------------
# 3. Define Endpoints
# ------------------------------------------------------------------------------

@app.get("/", summary="Root Health Check")
def read_root():
    """
    Root endpoint for PathAI.
    
    What it does:
    Returns a simple JSON payload confirming that the server is alive and reachable.
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
    summary="Receive and Validate Learning Plan Configuration",
)
def submit_plan_request(request: PlanRequest) -> PlanResponse:
    """
    Receives and validates the user's learning goal and constraints.
    
    Flow:
    [ Frontend sends JSON ]
            │
            ▼
    [ Pydantic inspects fields (PlanRequest) ]
      ├── Invalid: FastAPI immediately returns HTTP 422 with error details
      └── Valid: Continues to this function
            │
            ▼
    [ Returns confirmation message with validated data ]
    
    Args:
        request (PlanRequest): The validated request payload.
        
    Returns:
        PlanResponse: Confirmation message and echo of the validated data.
    """
    return PlanResponse(
        message="Learning plan request received",
        data=request,
    )
