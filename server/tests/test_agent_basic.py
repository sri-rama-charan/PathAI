# ==============================================================================
# File: server/tests/test_agent_basic.py
# Purpose: Basic evaluation test for PathAI AI curriculum generator (app.services.llm).
# ==============================================================================

import datetime
from unittest.mock import MagicMock, patch
import pytest

from app.schemas import PlanRequest, PlanResult, LearningPlan, DayPlan
from app.services.llm import generate_learning_plan


def _build_mock_gemini_response() -> MagicMock:
    """
    Creates a mock Gemini response containing a valid 7-day React learning plan JSON.
    """
    mock_json = """{
      "feasible": true,
      "feasibilityMessage": "7 days with 2 hours per day is sufficient for React fundamentals.",
      "estimatedRequiredHours": 14.0,
      "availableHours": 14.0,
      "recommendations": [],
      "plan": {
        "title": "React Fundamentals 7-Day Curriculum",
        "overview": "Comprehensive 7-day curriculum covering React components, JSX, state, and hooks.",
        "prerequisites": ["HTML/CSS", "JavaScript ES6"],
        "days": [
          {
            "day": 1,
            "date": "2026-09-21",
            "topic": "Introduction to React & JSX",
            "objectives": ["Understand Virtual DOM and JSX syntax"],
            "tasks": ["Set up Vite React template", "Build your first component"],
            "estimatedHours": 2.0
          },
          {
            "day": 2,
            "date": "2026-09-22",
            "topic": "Components & Props",
            "objectives": ["Understand functional components and prop passing"],
            "tasks": ["Create a UserCard component with props"],
            "estimatedHours": 2.0
          },
          {
            "day": 3,
            "date": "2026-09-23",
            "topic": "State Management with useState",
            "objectives": ["Learn local component state and reactivity"],
            "tasks": ["Build an interactive Counter component"],
            "estimatedHours": 2.0
          },
          {
            "day": 4,
            "date": "2026-09-24",
            "topic": "Handling Form Inputs & Events",
            "objectives": ["Handle event listeners and controlled inputs"],
            "tasks": ["Create a controlled input form with submit handler"],
            "estimatedHours": 2.0
          },
          {
            "day": 5,
            "date": "2026-09-25",
            "topic": "Side Effects with useEffect",
            "objectives": ["Understand useEffect lifecycle and dependencies"],
            "tasks": ["Fetch public API data on component mount"],
            "estimatedHours": 2.0
          },
          {
            "day": 6,
            "date": "2026-09-26",
            "topic": "Lifting State & Array Rendering",
            "objectives": ["Pass callbacks to parent and render dynamic lists"],
            "tasks": ["Build a dynamic Todo list manager"],
            "estimatedHours": 2.0
          },
          {
            "day": 7,
            "date": "2026-09-27",
            "topic": "Capstone Mini-Project",
            "objectives": ["Combine state, hooks, and props into a capstone app"],
            "tasks": ["Complete interactive Task Tracker capstone"],
            "estimatedHours": 2.0
          }
        ]
      }
    }"""
    mock_res = MagicMock()
    mock_res.text = mock_json
    return mock_res


@patch("app.services.llm.get_gemini_client")
def test_agent_basic_react_plan(mock_get_client):
    """
    Evaluates that generate_learning_plan creates a valid 7-day curriculum matching all requirements.
    """
    # Arrange: Mock Gemini API client response
    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.return_value = _build_mock_gemini_response()
    mock_get_client.return_value = mock_client_instance

    # Arrange: Input request schema matching user specification
    request = PlanRequest(
        goal="Learn React",
        experience="Beginner",
        durationDays=7,
        hoursPerDay=2,
        startDate=datetime.date(2026, 9, 21),
        resourcePreferences=["videos", "documentation"],
    )

    # Act: Invoke the core learning plan generator
    result = generate_learning_plan(request)

    # Verify 1: The agent completes successfully and returns a PlanResult
    assert isinstance(result, PlanResult)

    # Verify 2: A learning plan is returned and marked feasible
    assert result.feasible is True
    assert result.plan is not None
    assert isinstance(result.plan, LearningPlan)

    # Verify 3: The plan contains exactly 7 days
    days = result.plan.days
    assert len(days) == 7

    # Verify 4: Day numbers are sequential from 1 to 7
    expected_days = list(range(1, 8))
    actual_days = [d.day for d in days]
    assert actual_days == expected_days

    # Verify 5: Dates are sequential starting from 2026-09-21
    start_dt = datetime.date(2026, 9, 21)
    expected_dates = [start_dt + datetime.timedelta(days=i) for i in range(7)]
    actual_dates = [d.date for d in days]
    assert actual_dates == expected_dates

    # Verify 6: Every day has a non-empty topic
    for day in days:
        assert isinstance(day.topic, str)
        assert len(day.topic.strip()) > 0

    # Verify 7: Every day has objectives and tasks
    for day in days:
        assert isinstance(day.objectives, list)
        assert len(day.objectives) > 0
        assert isinstance(day.tasks, list)
        assert len(day.tasks) > 0

    # Verify 8: estimatedHours for every day is > 0 and does not exceed 2
    for day in days:
        assert 0.0 < float(day.estimatedHours) <= 2.0

    # Verify 9: The final result has the expected LearningPlan structure
    assert isinstance(result.plan.title, str) and len(result.plan.title) > 0
    assert isinstance(result.plan.overview, str) and len(result.plan.overview) > 0
    assert isinstance(result.plan.prerequisites, list)
