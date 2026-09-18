# ==============================================================================
# File: server/Dockerfile
# Purpose: Production Dockerfile for PathAI FastAPI backend server.
# Single-process Uvicorn execution preserving in-memory OAuth token state.
# ==============================================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install dependencies first for Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY app ./app

# Expose default port
EXPOSE 8000

# Execute single-worker Uvicorn using shell form for dynamic PORT expansion
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
