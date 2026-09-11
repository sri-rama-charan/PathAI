# ==============================================================================
# File: server/app/main.py
# Purpose: Entry point for the PathAI FastAPI backend server.
#
# What this file does:
# 1. Creates the FastAPI application instance.
# 2. Configures CORS (Cross-Origin Resource Sharing) so our React frontend can talk to it.
# 3. Defines the root ("/") endpoint confirming the backend is up and running.
# 4. Exposes automatic interactive API documentation at "/docs".
# ==============================================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ------------------------------------------------------------------------------
# 1. Create the FastAPI Application
# ------------------------------------------------------------------------------
# The FastAPI object is the central hub of our backend application.
# It manages routing, middleware, request validation, and documentation generation.
app = FastAPI(
    title="PathAI Backend",
    description="Backend API for PathAI — AI Learning Path Generator",
    version="0.1.0",
)

# ------------------------------------------------------------------------------
# 2. Configure CORS (Cross-Origin Resource Sharing)
# ------------------------------------------------------------------------------
# Why this is needed:
# By default, web browsers block a frontend running at http://localhost:5173 from
# calling an API running at http://localhost:8000 because they are on different ports
# ("different origins"). CORS middleware explicitly tells the browser: "It is safe
# for our frontend to talk to this backend."
origins = [
    "http://localhost:5173",  # Default Vite dev server URL
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all HTTP headers
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
    
    Returns:
        dict: A JSON object with a status message and service details.
    """
    return {
        "status": "online",
        "message": "PathAI backend is running successfully!",
        "service": "PathAI",
        "docs_url": "/docs",
    }
