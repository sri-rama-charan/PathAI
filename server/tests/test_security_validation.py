# ==============================================================================
# File: server/tests/test_security_validation.py
# Purpose: Pytest unit tests for input payload length limits and Pydantic validation.
# ==============================================================================

import datetime
import pytest
from pydantic import ValidationError

from app.schemas import (
    PlanRequest,
    ResearchRequest,
    PlanModifyRequest,
    LearningPlan,
    DayPlan,
)


def test_input_under_2000_characters_accepted():
    """
    Verifies that inputs with lengths under 2000 characters are accepted by Pydantic models.
    """
    valid_goal = "Learn Python " * 50  # ~650 characters
    valid_exp = "Beginner with basic coding " * 40  # ~1080 characters

    req = PlanRequest(
        goal=valid_goal,
        experience=valid_exp,
        durationDays=7,
        hoursPerDay=2.0,
        startDate=datetime.date(2026, 9, 21),
    )
    assert req.goal.strip() == valid_goal.strip()
    assert req.experience.strip() == valid_exp.strip()

    valid_query = "How to use LangGraph " * 50
    research_req = ResearchRequest(query=valid_query)
    assert research_req.query.strip() == valid_query.strip()


def test_input_exceeding_2000_characters_rejected():
    """
    Verifies that inputs exceeding 2000 characters are rejected with Pydantic ValidationError.
    """
    over_limit_text = "A" * 2001

    # 1. PlanRequest goal over limit
    with pytest.raises(ValidationError) as exc_info:
        PlanRequest(
            goal=over_limit_text,
            experience="Beginner",
            durationDays=7,
            hoursPerDay=2.0,
            startDate=datetime.date(2026, 9, 21),
        )
    assert "String should have at most 2000 characters" in str(exc_info.value) or "max_length" in str(exc_info.value) or "2000" in str(exc_info.value)

    # 2. PlanRequest experience over limit
    with pytest.raises(ValidationError):
        PlanRequest(
            goal="Learn React",
            experience=over_limit_text,
            durationDays=7,
            hoursPerDay=2.0,
            startDate=datetime.date(2026, 9, 21),
        )

    # 3. ResearchRequest query over limit
    with pytest.raises(ValidationError):
        ResearchRequest(query=over_limit_text)

    # 4. PlanModifyRequest feedback over limit
    dummy_plan = LearningPlan(
        title="React Plan",
        overview="Overview",
        prerequisites=[],
        days=[
            DayPlan(
                day=1,
                date=datetime.date(2026, 9, 21),
                topic="React Basics",
                objectives=["Understand JSX"],
                tasks=["Build hello world"],
                estimatedHours=2.0,
            )
        ],
    )
    with pytest.raises(ValidationError):
        PlanModifyRequest(
            currentPlan=dummy_plan,
            feedback=over_limit_text,
            durationDays=1,
            hoursPerDay=2.0,
            startDate=datetime.date(2026, 9, 21),
        )
