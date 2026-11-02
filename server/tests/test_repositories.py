# ==============================================================================
# File: server/tests/test_repositories.py
# Purpose: Unit tests for plan_repository and calendar_repository operations.
# ==============================================================================

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.models.learning_plan import LearningPlanModel
from app.repositories.plan_repository import (
    create_learning_plan,
    get_all_learning_plans,
    get_learning_plan_by_id,
    update_learning_plan,
    update_plan_google_doc_url,
)
from app.repositories.calendar_repository import (
    save_calendar_event_mappings,
    get_calendar_event_mappings,
)

TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_create_and_retrieve_learning_plan(db):
    """
    Tests creating a learning plan through repository and fetching by ID.
    """
    plan = create_learning_plan(
        db=db,
        title="Repository Test Plan",
        goal="Test Repository Layer",
        input_data={"durationDays": 3, "hoursPerDay": 2.0},
        plan_data={"days": [{"day": 1, "topic": "Intro"}]},
    )
    assert plan.id is not None
    assert plan.title == "Repository Test Plan"

    fetched = get_learning_plan_by_id(db, plan.id)
    assert fetched is not None
    assert fetched.id == plan.id
    assert fetched.goal == "Test Repository Layer"


def test_get_all_learning_plans_ordering(db):
    """
    Tests retrieving all plans ordered by newest first.
    """
    p1 = create_learning_plan(
        db=db,
        title="Plan 1",
        goal="Goal 1",
        input_data={},
        plan_data={},
    )
    p2 = create_learning_plan(
        db=db,
        title="Plan 2",
        goal="Goal 2",
        input_data={},
        plan_data={},
    )

    all_plans = get_all_learning_plans(db)
    assert len(all_plans) == 2
    # Newest first
    assert all_plans[0].id == p2.id
    assert all_plans[1].id == p1.id


def test_update_learning_plan_in_place(db):
    """
    Tests updating an existing learning plan in-place without creating duplicates.
    """
    plan = create_learning_plan(
        db=db,
        title="Original Title",
        goal="Learn Rust",
        input_data={"durationDays": 5},
        plan_data={"days": []},
    )
    plan_id = plan.id

    updated = update_learning_plan(
        db=db,
        plan_id=plan_id,
        title="Updated Title",
        plan_data={"days": [{"day": 1, "topic": "Rust Syntax"}]},
    )
    assert updated is not None
    assert updated.id == plan_id
    assert updated.title == "Updated Title"
    assert len(updated.plan_data["days"]) == 1

    # Verify no duplicate was created
    assert len(get_all_learning_plans(db)) == 1


def test_update_plan_google_doc_url(db):
    """
    Tests updating the google_doc_url on a plan.
    """
    plan = create_learning_plan(
        db=db,
        title="Doc URL Plan",
        goal="Docs Test",
        input_data={},
        plan_data={},
    )
    assert plan.google_doc_url is None

    doc_url = "https://docs.google.com/document/d/test-doc-id/edit"
    updated = update_plan_google_doc_url(db, plan.id, doc_url)
    assert updated is not None
    assert updated.google_doc_url == doc_url


def test_calendar_repository_save_and_retrieve(db):
    """
    Tests saving and retrieving Google Calendar event mappings through repository.
    """
    plan = create_learning_plan(
        db=db,
        title="Calendar Mappings Plan",
        goal="Schedule Test",
        input_data={},
        plan_data={"days": [{"day": 1, "topic": "Day 1"}]},
    )

    mock_events = [
        {"day": 1, "eventId": "event-123", "summary": "Study Session 1", "verified": True},
        {"day": 2, "eventId": "event-456", "summary": "Study Session 2", "verified": True},
    ]

    saved_plan = save_calendar_event_mappings(db, plan.id, mock_events)
    assert saved_plan is not None

    retrieved_events = get_calendar_event_mappings(db, plan.id)
    assert len(retrieved_events) == 2
    assert retrieved_events[0]["eventId"] == "event-123"
    assert retrieved_events[1]["eventId"] == "event-456"


def test_calendar_repository_nonexistent_plan(db):
    """
    Tests handling of nonexistent plan ID when managing calendar mappings.
    """
    res = save_calendar_event_mappings(db, 9999, [{"day": 1}])
    assert res is None

    empty = get_calendar_event_mappings(db, 9999)
    assert empty == []

