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

from app.schemas import PlanRequest, PlanResult, LearningPlan, PlanModifyRequest

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


# ==============================================================================
# Plan Modification Service
# ==============================================================================

MODIFY_SYSTEM_INSTRUCTION = """
You are PathAI, an expert AI learning-path architect.
You are being asked to MODIFY an existing learning plan based on user feedback.

Rules you MUST follow:
1. Preserve the original learning goal — do not change what the learner is studying.
2. Preserve the exact number of days — the modified plan must have the same number of day entries.
3. Preserve the start date — Day 1 must remain on the same calendar date.
4. Preserve the daily hours limit — no day's estimatedHours may exceed hoursPerDay.
5. Keep sequential day numbers starting from 1.
6. Keep sequential calendar dates (each day advances by exactly 1 calendar day).
7. Apply the user's feedback where reasonable — do not ignore it.
8. Do not invent wholesale changes unrelated to the feedback.
9. Return a complete, valid PlanResult with feasible=true and a full plan.
   (Modification requests are only made when the original plan was already feasible.)
10. Set feasibilityMessage to a brief sentence explaining what was changed.
""".strip()


def _serialise_existing_plan(request: PlanModifyRequest) -> str:
    """
    Converts the existing LearningPlan into a readable text block so Gemini
    can see exactly what it is modifying rather than starting from scratch.
    """
    plan = request.currentPlan
    lines = [
        f"Title: {plan.title}",
        f"Overview: {plan.overview}",
        f"Prerequisites: {', '.join(plan.prerequisites) if plan.prerequisites else 'None'}",
        "",
        "Existing daily schedule:",
    ]
    for day in plan.days:
        lines.append(f"\n  Day {day.day} — {day.date} — {day.topic} ({day.estimatedHours} hrs)")
        for obj in day.objectives:
            lines.append(f"    • Objective: {obj}")
        for task in day.tasks:
            lines.append(f"    ▸ Task: {task}")
    return "\n".join(lines)


def validate_modified_plan(plan: LearningPlan, request: PlanModifyRequest) -> None:
    """
    Raises ValueError with a descriptive message if the modified plan violates
    any hard constraints. Does NOT silently clamp — failures surface as errors.
    """
    available_hours = round(float(request.durationDays) * float(request.hoursPerDay), 2)

    if len(plan.days) != request.durationDays:
        raise ValueError(
            f"Modified plan has {len(plan.days)} days but the original had "
            f"{request.durationDays}. The number of days must be preserved."
        )

    total_hours = 0.0
    for i, day in enumerate(plan.days):
        expected_day_num = i + 1
        if day.day != expected_day_num:
            raise ValueError(
                f"Day numbering is not sequential: expected day {expected_day_num}, "
                f"got day {day.day}."
            )

        expected_date = request.startDate + datetime.timedelta(days=i)
        if day.date != expected_date:
            raise ValueError(
                f"Day {day.day} has date {day.date} but expected {expected_date}. "
                f"Dates must remain sequential from the original start date."
            )

        if not day.topic or not day.topic.strip():
            raise ValueError(f"Day {day.day} is missing a topic.")

        if day.estimatedHours <= 0:
            raise ValueError(f"Day {day.day} has non-positive estimatedHours ({day.estimatedHours}).")

        if day.estimatedHours > request.hoursPerDay:
            raise ValueError(
                f"Day {day.day} estimatedHours ({day.estimatedHours}) exceeds the "
                f"daily limit of {request.hoursPerDay} hrs."
            )

        if not day.objectives:
            raise ValueError(f"Day {day.day} has no objectives.")

        if not day.tasks:
            raise ValueError(f"Day {day.day} has no tasks.")

        total_hours += day.estimatedHours

    if round(total_hours, 1) > round(available_hours + 0.5, 1):
        raise ValueError(
            f"Total estimated hours ({total_hours:.1f}) exceed available hours "
            f"({available_hours:.1f})."
        )


def modify_learning_plan(request: PlanModifyRequest) -> PlanResult:
    """
    Sends the existing plan + user feedback to Gemini and returns a validated,
    modified PlanResult.

    Flow:
      1. Serialise the existing plan into a readable prompt block.
      2. Instruct Gemini to MODIFY (not replace) the plan per the feedback.
      3. Parse the structured PlanResult response.
      4. Run deterministic Python validation (validate_modified_plan).
      5. Re-apply date/day/hours corrections (validate_and_fix_plan_deterministically).
      6. Return the validated PlanResult.

    Raises:
      ValueError: Blank feedback, parse failure, or constraint violation.
      RuntimeError: Gemini API failure across all fallback models.
    """
    available_hours = round(float(request.durationDays) * float(request.hoursPerDay), 2)
    client = get_gemini_client()

    primary_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip() or "gemini-2.0-flash"
    fallback_models = list(dict.fromkeys([
        primary_model,
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
    ]))

    existing_plan_text = _serialise_existing_plan(request)

    prompt = f"""
You are modifying an existing {request.durationDays}-day learning plan.

CONSTRAINTS (must be preserved exactly):
- Start date: {request.startDate.isoformat()}
- Duration: {request.durationDays} days
- Daily hours limit: {request.hoursPerDay} hrs/day
- Total available hours: {available_hours:.1f} hrs

USER FEEDBACK (what to change):
"{request.feedback.strip()}"

EXISTING PLAN TO MODIFY:
{existing_plan_text}

Instructions:
- Apply the user's feedback to modify the plan.
- Do NOT change the number of days, start date, or daily hours limit.
- Do NOT invent changes the user did not request.
- Return feasible=true and a complete modified LearningPlan.
- Set feasibilityMessage to one sentence describing what was changed.
- estimatedRequiredHours should equal {available_hours:.1f} (available hours).
- availableHours should equal {available_hours:.1f}.
""".strip()

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
                    system_instruction=MODIFY_SYSTEM_INSTRUCTION,
                    temperature=0.3,
                ),
            )
            if response and response.text:
                break
        except Exception as exc:
            last_error = exc
            continue

    if not response or not response.text:
        raise RuntimeError(
            f"Gemini API modification failed across all fallback models: {last_error}"
        )

    try:
        plan_result = PlanResult.model_validate_json(response.text)
    except Exception as parse_err:
        raise ValueError(
            f"Failed to parse Gemini structured output for modification: {parse_err}"
        ) from parse_err

    if not plan_result.feasible or plan_result.plan is None:
        raise ValueError(
            "Gemini returned an infeasible result for a modification request. "
            "This is unexpected — the original plan was already feasible."
        )

    # Strict structural validation (raises on constraint violations)
    validate_modified_plan(plan_result.plan, request)

    # Re-apply deterministic corrections (day numbers, dates, hour caps)
    # We create a minimal PlanRequest-like object to reuse the existing helper.
    minimal_request = PlanRequest(
        goal="(plan modification)",
        experience="(plan modification)",
        durationDays=request.durationDays,
        hoursPerDay=request.hoursPerDay,
        startDate=request.startDate,
        resourcePreferences=[],
    )
    validated_result = validate_and_fix_plan_deterministically(
        plan_result, minimal_request, available_hours
    )
    return validated_result

