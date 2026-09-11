# PathAI — AI Learning Path Generator

PathAI is an intelligent, agent-driven application designed to help users master new skills. Given a learning goal and personal constraints (such as available time, budget, and prior experience), PathAI researches learning resources, synthesizes a structured curriculum, seeks user approval, and automatically organizes learning schedules into Google Docs and Google Calendar.

---

## Current Development Status

- **Stage**: Milestone 1 — Project Foundation & Boilerplate
- **Status**: Clean baseline initialized with a React + TypeScript frontend and a FastAPI backend.
- **Next Up**: Connecting the frontend and backend with a live health-check handshake, followed by our first single-prompt LLM connection.

---

## Current Technology Stack

### Frontend (`client/`)
- **React 18/19**: Declarative user interface library.
- **TypeScript**: Static typing for safer, bug-free JavaScript.
- **Vite**: Ultra-fast frontend development server and bundler.
- **Tailwind CSS**: Utility-first CSS framework for clean styling.

### Backend (`server/`)
- **Python 3.11+**: Primary programming language for our backend and AI workflows.
- **FastAPI**: Modern, fast web framework for building REST APIs with automatic OpenAPI/Swagger documentation.
- **Uvicorn**: High-performance ASGI web server to serve FastAPI.

---

## Project Structure

```text
PathAI/
├── .gitignore              # Single root Git ignore (ignores .venv, node_modules, caches)
├── README.md               # Project documentation and quick start guide
├── client/                 # Frontend React + TypeScript application
│   ├── index.html          # Web page HTML template
│   ├── package.json        # Frontend dependencies and scripts
│   ├── vite.config.ts      # Vite configuration (React + Tailwind plugins)
│   ├── tsconfig.json       # Single, unified TypeScript configuration
│   └── src/
│       ├── main.tsx        # React mounting entry point
│       ├── App.tsx         # Simple placeholder page
│       └── index.css       # Tailwind CSS styling setup
└── server/                 # Backend Python + FastAPI application
    ├── requirements.txt    # Minimal Python dependencies (fastapi, uvicorn)
    └── app/
        ├── __init__.py     # Marks 'app' as a Python package
        └── main.py         # FastAPI application entry point with GET / endpoint
```

---

## How to Run Locally

### 1. Start the Backend (FastAPI)

Open a terminal in the root folder:

```powershell
# Navigate to the server folder
cd server

# Create a Python virtual environment (if not already created)
python -m venv .venv

# Activate the virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the development server with auto-reload
uvicorn app.main:app --reload --port 8000
```

- API root: [http://localhost:8000/](http://localhost:8000/)
- Interactive API Documentation (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)

---

### 2. Start the Frontend (React + Vite)

Open a second terminal in the root folder:

```powershell
# Navigate to the client folder
cd client

# Install dependencies (if not already installed)
npm install

# Start the Vite development server
npm run dev
```

- Frontend application: [http://localhost:5173/](http://localhost:5173/)
