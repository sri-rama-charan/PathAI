# ==============================================================================
# File: server/app/services/llm.py
# Purpose: Google Gemini integration for learning-plan feasibility and curriculum generation.
#
# What this service does:
# 1. Dynamically reloads GEMINI_API_KEY and GEMINI_MODEL from server/.env.
# 2. Instructs Gemini to evaluate goal feasibility and generate structured output (PlanResult).
# 3. Performs deterministic Python validation on calendar dates, sequential days, and hours.
# 4. Handles missing API keys or LLM provider errors gracefully.
# ==============================================================================

import os
import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.schemas import PlanRequest, PlanResult, LearningPlan

# Resolve path to server directory
SERVER_DIR = Path(__file__).resolve().parent.parent.parent


def get_gemini_client() -> genai.Client:
    """
    Dynamically reloads server/.env and initializes the Gemini client.
    
    Why reload here:
    Allows changes in server/.env (like adding an API key) to take effect
    immediately without requiring a manual server restart.
    
    Raises:
        ValueError: If GEMINI_API_KEY is not configured or is a placeholder.
    """
    load_dotenv(SERVER_DIR / ".env", override=True)
    load_dotenv(override=True)
    
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY is not set. Please create a .env file in the server/ directory "
            "with a valid Google Gemini API key: GEMINI_API_KEY=your_key"
        )
        
    return genai.Client(api_key=api_key)


SYSTEM_INSTRUCTION = """
You are PathAI, an expert AI learning-path architect.
Your mission is to evaluate a learner's goal and constraints, determine whether their available time is feasible, and if feasible, generate a comprehensive, progressive curriculum.

Guidelines:
1. Compare the user's target goal and current experience against their total available hours:
   availableHours = durationDays * hoursPerDay.
2. Feasibility Evaluation:
   - If the estimated hours required significantly exceed availableHours (or the goal is far too broad for the timeframe), set feasible=false, plan=null.
   - Explain clearly in feasibilityMessage why the timeframe is insufficient.
   - Provide estimatedRequiredHours (e.g. 80.0) and availableHours.
   - Provide at least 2 practical, actionable recommendations (e.g. suggested duration extension, narrowing curriculum scope to essential fundamentals).
3. When Feasible:
   - Set feasible=true.
   - Set plan to a complete LearningPlan containing title, overview, prerequisites, and exactly durationDays items in the 'days' array.
   - Day 1 must start on startDate. Each subsequent day must advance by exactly 1 calendar day.
   - Each day's estimatedHours must not exceed hoursPerDay.
   - Tailor the study exercises and topics to the user's preferred resources (e.g. videos, documentation, courses, projects).
   - Structure the curriculum with logical pedagogical progression: foundations -> core architecture -> hands-on implementation -> capstone projects.
4. Tone & Philosophy:
   - Be constructive, motivating, and realistic. Never claim learning hour estimates are exact guarantees.
""".strip()


def build_user_prompt(request: PlanRequest, available_hours: float) -> str:
    """
    Formats user constraints into a clear prompt for the LLM.
    """
    prefs = ", ".join(request.resourcePreferences) if request.resourcePreferences else "Any / general resources"
    
    return f"""
Target Learning Goal: {request.goal}
Current Knowledge / Background: {request.experience}
Target Start Date: {request.startDate.isoformat()}
Duration: {request.durationDays} days
Daily Study Time: {request.hoursPerDay} hours/day
Total Available Study Time: {available_hours:.1f} hours
Resource Preferences: {prefs}

Please evaluate the feasibility of mastering this goal within {available_hours:.1f} hours.
If feasible, generate the day-by-day learning plan. If not feasible, explain why and suggest adjustments.
""".strip()


def validate_and_fix_plan_deterministically(
    plan_result: PlanResult,
    request: PlanRequest,
    available_hours: float
) -> PlanResult:
    """
    Applies deterministic Python validation to ensure mathematical and temporal accuracy.
    """
    plan_result.availableHours = available_hours
    
    if not plan_result.feasible or plan_result.plan is None:
        plan_result.plan = None
        if plan_result.estimatedRequiredHours <= available_hours:
            plan_result.estimatedRequiredHours = round(available_hours * 1.5, 1)
        return plan_result
        
    plan = plan_result.plan
    validated_days = []
    
    for i, day in enumerate(plan.days):
        expected_date = request.startDate + datetime.timedelta(days=i)
        capped_hours = min(round(float(day.estimatedHours), 1), float(request.hoursPerDay))
        if capped_hours <= 0:
            capped_hours = round(float(request.hoursPerDay), 1)
            
        day.day = i + 1
        day.date = expected_date
        day.estimatedHours = capped_hours
        validated_days.append(day)
        
    plan.days = validated_days
    return plan_result


def generate_learning_plan(request: PlanRequest) -> PlanResult:
    """
    Coordinates Gemini LLM generation with deterministic Python validation.
    """
    available_hours = round(float(request.durationDays) * float(request.hoursPerDay), 2)
    client = get_gemini_client()
    
    # Read model from environment, defaulting to gemini-3.5-flash
    primary_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip() or "gemini-3.5-flash"
    fallback_models = [primary_model, "gemini-3.6-flash", "gemini-flash-latest"]
    
    prompt = build_user_prompt(request, available_hours)
    response = None
    last_error = None
    
    for model_name in fallback_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=PlanResult,
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.2,
                ),
            )
            if response and response.text:
                break
        except Exception as exc:
            last_error = exc
            continue

    if not response or not response.text:
        raise RuntimeError(f"Gemini API generation failed across models: {str(last_error)}")

    try:
        plan_result = PlanResult.model_validate_json(response.text)
    except Exception as parse_err:
        raise ValueError(f"Failed to parse Gemini structured output: {str(parse_err)}") from parse_err

    validated_result = validate_and_fix_plan_deterministically(plan_result, request, available_hours)
    return validated_result
