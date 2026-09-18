# ==============================================================================
# File: server/tests/test_agent_modification.py
# Purpose: Evaluation test for human-feedback plan modification (app.services.llm).
# ==============================================================================

import copy
import datetime
from unittest.mock import MagicMock, patch
import pytest

from app.schemas import DayPlan, LearningPlan, PlanModifyRequest, PlanResult
from app.services.llm import modify_learning_plan


def _build_original_3day_plan() -> LearningPlan:
    """
    Constructs a valid 3-day initial LearningPlan with theory-heavy tasks.
    """
    return LearningPlan(
        title="Python Theory Basics",
        overview="3-day theoretical overview of Python concepts.",
        prerequisites=["Basic literacy"],
        days=[
            DayPlan(
                day=1,
                date=datetime.date(2026, 9, 21),
                topic="Python Syntax Theory",
                objectives=["Read about variables and data types"],
                tasks=["Read documentation on variables"],
                estimatedHours=2.0,
            ),
            DayPlan(
                day=2,
                date=datetime.date(2026, 9, 22),
                topic="Control Flow Theory",
                objectives=["Understand if-else statements conceptually"],
                tasks=["Read chapter on conditional execution"],
                estimatedHours=2.0,
            ),
            DayPlan(
                day=3,
                date=datetime.date(2026, 9, 23),
                topic="Functions Theory",
                objectives=["Study function definition syntax"],
                tasks=["Review theoretical function documentation"],
                estimatedHours=2.0,
            ),
        ],
    )


def _build_mock_gemini_modified_response() -> MagicMock:
    """
    Mock Gemini response containing a revised 3-day LearningPlan with hands-on projects.
    """
    mock_json = """{
      "feasible": true,
      "feasibilityMessage": "Plan modified to include hands-on practical projects.",
      "estimatedRequiredHours": 6.0,
      "availableHours": 6.0,
      "recommendations": [],
      "plan": {
        "title": "Python Hands-On Projects",
        "overview": "Revised 3-day curriculum focused on hands-on project implementation.",
        "prerequisites": ["Basic literacy"],
        "days": [
          {
            "day": 1,
            "date": "2026-09-21",
            "topic": "Python Syntax & Calculator Project",
            "objectives": ["Build a CLI calculator project using variables"],
            "tasks": ["Implement a hands-on command line calculator project"],
            "estimatedHours": 2.0
          },
          {
            "day": 2,
            "date": "2026-09-22",
            "topic": "Control Flow & Quiz Game Project",
            "objectives": ["Build an interactive quiz game project"],
            "tasks": ["Develop a hands-on Python quiz game project"],
            "estimatedHours": 2.0
          },
          {
            "day": 3,
            "date": "2026-09-23",
            "topic": "Functions & Utility Tool Capstone Project",
            "objectives": ["Build a functional file parser utility project"],
            "tasks": ["Complete a hands-on project building a file parser tool"],
            "estimatedHours": 2.0
          }
        ]
      }
    }"""
    mock_res = MagicMock()
    mock_res.text = mock_json
    return mock_res


@patch("app.services.llm.get_gemini_client")
def test_modify_learning_plan_with_human_feedback(mock_get_client):
    """
    Evaluates that modify_learning_plan processes human feedback, applies requested changes
    (hands-on projects), preserves original schedule constraints, and does not mutate the original plan object.
    """
    # Arrange: Mock Gemini API client
    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.return_value = _build_mock_gemini_modified_response()
    mock_get_client.return_value = mock_client_instance

    # Arrange: Original 3-day plan and deepcopy snapshot for immutability check
    original_plan = _build_original_3day_plan()
    original_plan_snapshot = copy.deepcopy(original_plan)

    request = PlanModifyRequest(
        currentPlan=original_plan,
        feedback="Add more hands-on projects and reduce theory.",
        durationDays=3,
        hoursPerDay=2.0,
        startDate=datetime.date(2026, 9, 21),
    )

    # Act: Invoke backend modification function
    result = modify_learning_plan(request)

    # Assert 1: Function completes successfully and returns a PlanResult
    assert isinstance(result, PlanResult)

    # Assert 2: A LearningPlan is returned
    assert result.feasible is True
    assert result.plan is not None
    assert isinstance(result.plan, LearningPlan)

    # Assert 3: Modified plan contains exactly 3 days
    modified_days = result.plan.days
    assert len(modified_days) == 3

    # Assert 4: Day numbers remain 1, 2, 3
    assert [d.day for d in modified_days] == [1, 2, 3]

    # Assert 5: Dates remain unchanged (2026-09-21, 2026-09-22, 2026-09-23)
    expected_dates = [
        datetime.date(2026, 9, 21),
        datetime.date(2026, 9, 22),
        datetime.date(2026, 9, 23),
    ]
    assert [d.date for d in modified_days] == expected_dates

    # Assert 6: Goal/duration/hours-per-day constraints are preserved
    total_hours = sum(d.estimatedHours for d in modified_days)
    assert total_hours <= 6.0
    for day in modified_days:
        assert 0.0 < day.estimatedHours <= 2.0

    # Assert 7: Modified plan contains requested change (hands-on project tasks)
    has_project_tasks = any(
        "project" in task.lower() or "hands-on" in task.lower()
        for day in modified_days
        for task in day.tasks
    )
    assert has_project_tasks is True

    # Assert 8: Modified plan remains valid according to Pydantic schema
    assert isinstance(result.plan.title, str) and len(result.plan.title) > 0
    assert isinstance(result.plan.overview, str) and len(result.plan.overview) > 0
    assert isinstance(result.plan.prerequisites, list)

    # Assert 9: Original plan object was not mutated
    assert original_plan == original_plan_snapshot
    assert original_plan.title == "Python Theory Basics"
    assert original_plan.days[0].topic == "Python Syntax Theory"
