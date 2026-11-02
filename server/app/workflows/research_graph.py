# ==============================================================================
# File: server/app/workflows/research_graph.py
# Purpose: LangGraph workflow for PathAI — Research Pipeline with Evaluation Loop.
#
# Workflow Structure:
#   START
#     ↓
#   analyze_goal         (LLM: understand intent + produce initial search query)
#     ↓
#   search_resources     (Python: execute search_web via Tavily)
#     ↓
#   evaluate_resources   (LLM: are results sufficient? produce refined query if not)
#     ↓
#   route_after_evaluation  ← conditional edge
#     ├── YES (sufficient or retries exhausted) → generate_response → END
#     └── NO  (insufficient, retries remain)    → search_resources → evaluate_resources → …
#
# Key Architectural Concepts:
# 1. State:  TypedDict — single source of truth passed between every node.
# 2. Nodes:  Pure Python functions that receive state and return partial updates.
# 3. Edges:  LangGraph controls flow. Conditional edges let the graph branch.
# 4. Loop:   evaluate_resources + route_after_evaluation create a retry loop
#            bounded by MAX_RETRIES so the graph always terminates.
# ==============================================================================

import json
import logging
import os
import time
from typing import List, Optional

from google.genai import types
from langgraph.graph import END, START, StateGraph

from app.integrations.gemini import get_gemini_client
from app.schemas.plan import SearchResult
from app.services.search import search_web
from app.workflows.states import ResearchState

# Configure logger for the research graph module
logger = logging.getLogger(__name__)

# Maximum number of search-evaluate cycles before forcing generation.
MAX_RETRIES = 2


# ------------------------------------------------------------------------------
# 1. Helper: Resilient LLM Generation with model fallback
# ------------------------------------------------------------------------------

def _generate_with_fallback(prompt: str, system_instruction: str = "") -> str:
    """
    Calls Gemini to generate text. Tries a prioritised list of flash-lite
    models so that rate-limits or empty responses on one model do not crash
    the whole workflow.

    Handles the "model output must contain either output text or tool calls"
    error by catching empty responses (finish_reason != STOP) and continuing
    to the next candidate model instead of raising immediately.

    NOTE: This helper intentionally uses freeform text generation (no
    response_schema), which is different from integrations/gemini.py's
    generate_structured_content() that enforces a Pydantic schema.
    """
    client = get_gemini_client()
    primary_model = (
        os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
        or "gemini-2.5-flash"
    )
    candidate_models = [
        primary_model,
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-3.5-flash-lite",
        "gemini-flash-latest",
    ]
    # Deduplicate while preserving order
    fallback_models: List[str] = list(dict.fromkeys(candidate_models))

    last_error: Optional[Exception] = None

    for model_name in fallback_models:
        try:
            config = types.GenerateContentConfig(
                temperature=0.2,
                system_instruction=system_instruction if system_instruction else None,
            )
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )

            # Guard: .text raises when finish_reason != STOP
            # (e.g. MAX_TOKENS, SAFETY, OTHER). Catch and try the next model.
            text: Optional[str] = None
            try:
                text = response.text
            except Exception:
                pass

            if text and text.strip():
                return text.strip()

            # Surface the actual stop reason for easier debugging
            finish_reason = "unknown"
            try:
                finish_reason = str(response.candidates[0].finish_reason)
            except Exception:
                pass
            last_error = RuntimeError(
                f"Model '{model_name}' returned empty output "
                f"(finish_reason={finish_reason})"
            )

        except Exception as exc:
            last_error = exc
            continue

    raise RuntimeError(
        f"Gemini generation failed across all fallback models: {last_error}"
    ) from last_error


# ------------------------------------------------------------------------------
# 2. Graph Nodes
# ------------------------------------------------------------------------------

def analyze_goal(state: ResearchState) -> dict:
    """
    Node 1: analyze_goal

    Uses Gemini to understand what the user is asking and produce:
      - A brief textual analysis of the learning goal.
      - An optimised initial search query for Tavily.

    Reads:   state["user_query"], state["run_id"]
    Updates: state["analysis"], state["search_query"]
    """
    node_start = time.perf_counter()
    run_id = state.get("run_id") or "unknown"
    user_query = state["user_query"]
    logger.info("[run: %s] [NODE: analyze_goal] Starting goal analysis...", run_id)

    prompt = f"""
You are an expert technical curriculum analyst.

A user has submitted this learning/research request:
"{user_query}"

Respond with ONLY a valid JSON object — no markdown, no code fences, no extra text:
{{
  "analysis": "<2-4 sentence analysis: core skill, ideal resource types, why it matters>",
  "search_query": "<optimised search query to find the best resources on this topic>"
}}
""".strip()

    raw = _generate_with_fallback(
        prompt=prompt,
        system_instruction="You are an expert technical curriculum analyzer. Always respond with valid JSON only.",
    )

    # Strip accidental markdown fences
    cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()

    try:
        parsed = json.loads(cleaned)
        analysis = parsed.get("analysis", raw)
        search_query = parsed.get("search_query", user_query)
    except (json.JSONDecodeError, AttributeError):
        # Fallback: use raw text as analysis and the user query as search query
        analysis = raw
        search_query = user_query

    elapsed = time.perf_counter() - node_start
    logger.info("[run: %s] [NODE: analyze_goal] Completed in %.2fs (generated query: '%s')", run_id, elapsed, search_query)

    return {
        "analysis": analysis,
        "search_query": search_query,
    }


def search_resources(state: ResearchState) -> dict:
    """
    Node 2: search_resources

    Deterministic Python — no LLM involved.
    Executes our search_web() service (Tavily) using the current search_query
    from state (set by analyze_goal or refined by evaluate_resources on retries).
    Handles search provider failures gracefully by returning an empty results list.

    Reads:   state["search_query"], state["user_query"] (fallback), state["run_id"]
    Updates: state["search_results"], state["retry_count"]
    """
    node_start = time.perf_counter()
    run_id = state.get("run_id") or "unknown"
    # Prefer the LLM-optimised search query; fall back to the raw user query
    query = state.get("search_query") or state["user_query"]
    current_retries = state.get("retry_count", 0)
    logger.info("[run: %s] [NODE: search_resources] Starting search (iteration %d, query: '%s')...", run_id, current_retries + 1, query)

    try:
        results: List[SearchResult] = search_web(query=query, max_results=5)
    except Exception as exc:
        logger.error("[run: %s] [NODE: search_resources] search_web failed during search execution: %s", run_id, exc)
        results = []

    elapsed = time.perf_counter() - node_start
    logger.info("[run: %s] [NODE: search_resources] Completed in %.2fs (%d results)", run_id, elapsed, len(results))

    return {
        "search_results": results,
        "retry_count": current_retries + 1,
    }


def evaluate_resources(state: ResearchState) -> dict:
    """
    Node 3: evaluate_resources

    Uses Gemini to judge whether the retrieved search results are sufficient
    to answer the user's query. If not, it also proposes a better search query
    for the next iteration.

    Reads:   state["user_query"], state["search_results"], state["run_id"]
    Updates: state["evaluation"]
    """
    node_start = time.perf_counter()
    run_id = state.get("run_id") or "unknown"
    user_query = state["user_query"]
    search_results = state.get("search_results", [])
    logger.info("[run: %s] [NODE: evaluate_resources] Starting evaluation for %d search results...", run_id, len(search_results))

    formatted = []
    for i, res in enumerate(search_results, 1):
        formatted.append(
            f"Result {i}:\n"
            f"  Title: {res.title}\n"
            f"  URL: {res.url}\n"
            f"  Summary: {res.description}\n"
        )
    results_text = "\n".join(formatted) if formatted else "No results were returned."

    prompt = f"""
You are evaluating search results to determine whether they adequately address a user's query.

User Query: "{user_query}"

Retrieved Results:
{results_text}

Assess the results:
- Are there at least 2-3 high-quality, directly relevant resources?
- Do the summaries actually address what the user is asking?

Respond with ONLY a valid JSON object — no markdown, no code fences:
{{
  "sufficient": true or false,
  "reason": "<one sentence explaining your verdict>",
  "better_search_query": "<a more targeted query string — only needed if sufficient is false, otherwise leave empty>"
}}
""".strip()

    raw = _generate_with_fallback(
        prompt=prompt,
        system_instruction="You are a strict search-quality evaluator. Respond with valid JSON only.",
    )

    cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()

    try:
        evaluation = json.loads(cleaned)
        # Normalise: ensure all expected keys exist
        evaluation.setdefault("sufficient", True)
        evaluation.setdefault("reason", "")
        evaluation.setdefault("better_search_query", "")
    except (json.JSONDecodeError, AttributeError):
        # If we can't parse the evaluation, treat results as sufficient
        # to avoid an infinite loop on a broken evaluator response.
        evaluation = {
            "sufficient": True,
            "reason": "Could not parse evaluation response; proceeding to generation.",
            "better_search_query": "",
        }

    sufficient: bool = evaluation.get("sufficient", True)
    reason: str = evaluation.get("reason", "")
    better_query: str = evaluation.get("better_search_query", "").strip()

    elapsed = time.perf_counter() - node_start
    logger.info("[run: %s] [NODE: evaluate_resources] Completed in %.2fs — verdict: sufficient=%s (reason: '%s')", run_id, elapsed, sufficient, reason)
    if not sufficient and better_query:
        logger.info("[run: %s] [NODE: evaluate_resources] Resources insufficient. Proposed refined query: '%s'", run_id, better_query)

    result_update = {"evaluation": evaluation}
    if not sufficient and better_query:
        result_update["search_query"] = better_query

    return result_update


def generate_response(state: ResearchState) -> dict:
    """
    Node 4: generate_response

    Uses Gemini to synthesise the final answer from the user's query,
    the goal analysis, and the retrieved search results.

    Reads:   state["user_query"], state["analysis"], state["search_results"], state["run_id"]
    Updates: state["final_answer"]
    """
    node_start = time.perf_counter()
    run_id = state.get("run_id") or "unknown"
    user_query = state["user_query"]
    analysis = state.get("analysis", "")
    search_results = state.get("search_results", [])
    logger.info("[run: %s] [NODE: generate_response] Starting final response synthesis with %d sources...", run_id, len(search_results))

    formatted_sources = []
    for i, res in enumerate(search_results, 1):
        formatted_sources.append(
            f"Resource {i}:\n"
            f"- Title: {res.title}\n"
            f"- URL: {res.url}\n"
            f"- Source: {res.source}\n"
            f"- Summary: {res.description}\n"
        )
    sources_context = (
        "\n".join(formatted_sources) if formatted_sources else "No web resources found."
    )

    prompt = f"""
User Question:
"{user_query}"

Topic Analysis:
{analysis}

Retrieved Web Resources:
{sources_context}

Please provide a well-structured, authoritative, and helpful answer for the user:
1. Introduce the key concepts and explain why mastering this topic is valuable.
2. Group the best resources into logical sections (e.g. Official Documentation, Structured Courses, Hands-on Tutorials/Tools).
3. Recommend a concrete, step-by-step learning progression (e.g. Phase 1, Phase 2, Phase 3).
4. Reference the retrieved resources with their titles and URLs where relevant.
""".strip()

    final_answer = _generate_with_fallback(
        prompt=prompt,
        system_instruction="You are PathAI's senior curriculum advisor. Provide rich, actionable learning roadmaps.",
    )

    elapsed = time.perf_counter() - node_start
    logger.info("[run: %s] [NODE: generate_response] Completed in %.2fs", run_id, elapsed)
    return {"final_answer": final_answer}


# ------------------------------------------------------------------------------
# 3. Conditional Router
# ------------------------------------------------------------------------------

def route_after_evaluation(state: ResearchState) -> str:
    """
    Conditional edge function called after evaluate_resources.

    Decision logic:
      - Results sufficient                          → "generate_response"
      - Results insufficient + retries remain       → "search_resources" (loop)
      - Results insufficient + retries exhausted    → "generate_response" (force end)

    Returns:
        The name of the next node to execute.
    """
    run_id = state.get("run_id") or "unknown"
    evaluation = state.get("evaluation") or {}
    sufficient: bool = evaluation.get("sufficient", True)
    retry_count: int = state.get("retry_count", 0)

    if sufficient:
        logger.info("[run: %s] [ROUTER: route_after_evaluation] Decision: 'generate_response' (results sufficient, retry_count: %d/%d)", run_id, retry_count, MAX_RETRIES)
        return "generate_response"

    if retry_count > MAX_RETRIES:
        logger.info("[run: %s] [ROUTER: route_after_evaluation] Decision: 'generate_response' (max retries %d reached, forcing generation)", run_id, MAX_RETRIES)
        return "generate_response"

    better_query = evaluation.get("better_search_query", "").strip()
    if better_query:
        state["search_query"] = better_query

    logger.info("[run: %s] [ROUTER: route_after_evaluation] Decision: 'search_resources' (retrying loop iteration %d/%d with refined query: '%s')", run_id, retry_count, MAX_RETRIES, better_query or state.get("search_query"))
    return "search_resources"


# ------------------------------------------------------------------------------
# 4. Build and Compile the StateGraph
# ------------------------------------------------------------------------------

def build_research_graph():
    """
    Constructs and compiles the LangGraph pipeline with evaluation loop.

    Flow:
        START
          → analyze_goal
          → search_resources
          → evaluate_resources
          → [conditional]
              ├── sufficient / retries_exhausted → generate_response → END
              └── insufficient / retries_remain  → search_resources  → … (loop)
    """
    workflow = StateGraph(ResearchState)

    # --- Register Nodes ---
    workflow.add_node("analyze_goal", analyze_goal)
    workflow.add_node("search_resources", search_resources)
    workflow.add_node("evaluate_resources", evaluate_resources)
    workflow.add_node("generate_response", generate_response)

    # --- Define Edges ---
    workflow.add_edge(START, "analyze_goal")
    workflow.add_edge("analyze_goal", "search_resources")
    workflow.add_edge("search_resources", "evaluate_resources")

    # Conditional edge: after evaluation, branch based on route_after_evaluation()
    workflow.add_conditional_edges(
        "evaluate_resources",
        route_after_evaluation,
        {
            "generate_response": "generate_response",
            "search_resources": "search_resources",
        },
    )

    workflow.add_edge("generate_response", END)

    return workflow.compile()


# Single compiled graph instance — imported by services/research_service.py
research_graph = build_research_graph()

