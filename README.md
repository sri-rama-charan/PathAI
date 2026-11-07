# PathAI — AI Learning Path Generator

PathAI is an intelligent, agent-driven application designed to help users master new skills. Given a learning goal and personal constraints (such as available time, budget, and prior experience), PathAI researches learning resources, synthesizes a structured curriculum, seeks user approval, and automatically organizes learning schedules into Google Docs and Google Calendar.

---

## Current Development Status

- **Stage**: Milestone 2 — AI Learning Plan & Feasibility Generation
- **Status**: Live integration with Google Gemini (`gemini-2.5-flash`) generating structured, validated daily curricula or constructive feasibility advice.
- **Next Up**: Introducing tools, web search for curated learning resources, and multi-step manual agent loops before moving to LangGraph.

---

## Current Technology Stack

### Frontend (`client/`)
- **React 18/19**: Declarative user interface library.
- **TypeScript**: Static typing for safer, bug-free JavaScript.
- **Vite**: Ultra-fast frontend development server and bundler.
- **Tailwind CSS**: Vercel Geist Design System styling tokens.
- **React Icons**: Minimalist Lucide vector icons (`react-icons/lu`).

### Backend (`server/`)
- **Python 3.11+**: Primary backend language.
- **FastAPI**: High-performance REST API with automated OpenAPI docs.
- **Uvicorn**: High-performance ASGI web server.
- **Google GenAI SDK (`google-genai`)**: Official Google Gemini Python SDK.
- **Pydantic v2**: Strict schema validation and structured LLM outputs.

---

## Project Structure

```text
PathAI/
├── .gitignore              # Single root Git ignore (ignores .venv, node_modules, caches)
├── README.md               # Project documentation and quick start guide
├── client/                 # Frontend React + TypeScript application
│   ├── index.html          # Web page HTML template with Geist font preloads
│   ├── package.json        # Frontend dependencies and scripts
│   ├── vite.config.ts      # Vite configuration (React + Tailwind plugins)
│   ├── tsconfig.json       # Unified TypeScript configuration
│   └── src/
│       ├── main.tsx        # React mounting entry point
│       ├── App.tsx         # Root view layout
│       ├── index.css       # Tailwind CSS & Geist design tokens
│       ├── types/
│       │   └── form.ts     # TypeScript interfaces for inputs, day plans, and API responses
│       ├── services/
│       │   └── api.ts      # Native fetch() API client connecting to FastAPI
│       └── components/
│           ├── layout/     # Header with brand mark
│           ├── ui/         # FormField and PreferenceChip components
│           └── forms/      # LearningPathForm and SubmissionPreview
└── server/                 # Backend Python + FastAPI application
    ├── requirements.txt    # Python dependencies (fastapi, uvicorn, google-genai)
    ├── .env.example        # Template for Gemini API credentials
    └── app/
        ├── __init__.py     # Package marker
        ├── main.py         # FastAPI application and route definitions
        ├── schemas.py      # Pydantic schemas (PlanRequest, DayPlan, PlanResult)
        └── services/
            ├── __init__.py # Services package marker
            └── llm.py      # Gemini integration & deterministic Python validation
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




Learning Path Generator

Purpose: Built an agentic learning planner for research, evaluation, retries, and personalized plan generation.

Technologies: React, Fast API, LangGraph, Gemini, Google Calendar API, JavaScript, Tailwind CSS

Features: 
- Personalized plan generation based on knowledge level and time availability
- Detailed Plan written in Google doc
- Automated Scheduling in Google Calendar
- Detailed Roadmap generation with suitable steps and corresponding resources for each step
- Daily remainders 
- Knowledge testing through quizzes and providing effective feedback
- Personalized AI Progress reports based on user's regular performance
