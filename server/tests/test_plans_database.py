# ==============================================================================
# File: server/tests/test_plans_database.py
# Purpose: Pytest test suite for PostgreSQL persistence and My Plans API endpoints.
# ==============================================================================

import datetime
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from app.models.learning_plan import LearningPlanModel
from app.main import app
from app.schemas.plan import PlanResult, LearningPlan, DayPlan

from sqlalchemy.pool import StaticPool

# Setup in-memory SQLite database with StaticPool so all sessions share the same test DB
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)



@pytest.fixture(scope="function")
def db_session():
    """
    Creates clean tables for each test and yields an isolated DB session.
    """
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    TestClient that overrides the get_db dependency with our test session.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _sample_learning_plan(title="Python Mastery 7-Day Plan") -> LearningPlan:
    return LearningPlan(
        title=title,
        overview="Learn foundational Python programming and OOP.",
        prerequisites=["Basic computer literacy"],
        days=[
            DayPlan(
                day=1,
                date=datetime.date(2026, 11, 1),
                topic="Python Syntax & Types",
                objectives=["Understand variables and numbers"],
                tasks=["Write hello world", "Declare variables"],
                estimatedHours=2.0,
            ),
            DayPlan(
                day=2,
                date=datetime.date(2026, 11, 2),
                topic="Control Flow",
                objectives=["If-else and loops"],
                tasks=["Build a guessing game"],
                estimatedHours=2.0,
            ),
        ],
    )


def test_automatic_plan_saving_on_successful_generation(client, db_session):
    """
    Verifies that when a feasible plan is generated, it is automatically persisted to PostgreSQL
    and its database primary key ID is returned to the frontend.
    """
    plan = _sample_learning_plan()
    mock_result = PlanResult(
        feasible=True,
        feasibilityMessage="Time is feasible for Python basics.",
        estimatedRequiredHours=4.0,
        availableHours=4.0,
        recommendations=[],
        plan=plan,
    )

    with patch("app.api.v1.plans.generate_learning_plan", return_value=mock_result):
        payload = {
            "goal": "Learn Python basics",
            "experience": "Beginner",
            "durationDays": 2,
            "hoursPerDay": 2.0,
            "startDate": "2026-11-01",
            "resourcePreferences": ["videos", "projects"],
        }
        response = client.post("/api/plan", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["planId"] is not None
        assert data["plan_id"] == data["planId"]
        plan_id = data["planId"]

        # Verify record exists in database
        record = db_session.query(LearningPlanModel).filter(LearningPlanModel.id == plan_id).first()
        assert record is not None
        assert record.title == "Python Mastery 7-Day Plan"
        assert record.goal == "Learn Python basics"
        assert record.input_data["durationDays"] == 2
        assert len(record.plan_data["days"]) == 2


def test_infeasible_plan_not_saved_to_database(client, db_session):
    """
    Verifies that infeasible plans (feasible=False, plan=None) are NOT saved to the database.
    """
    mock_result = PlanResult(
        feasible=False,
        feasibilityMessage="Not enough time to master quantum physics in 2 hours.",
        estimatedRequiredHours=100.0,
        availableHours=2.0,
        recommendations=["Increase duration to 30 days"],
        plan=None,
    )

    with patch("app.api.v1.plans.generate_learning_plan", return_value=mock_result):
        payload = {
            "goal": "Master Quantum Computing",
            "experience": "None",
            "durationDays": 1,
            "hoursPerDay": 2.0,
            "startDate": "2026-11-01",
            "resourcePreferences": ["books"],
        }
        response = client.post("/api/plan", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["planId"] is None

        count = db_session.query(LearningPlanModel).count()
        assert count == 0


def test_get_all_plans_empty_and_populated(client, db_session):
    """
    Verifies GET /api/plans returns an empty list initially and newest-first list when populated.
    """
    # 1. Empty state
    res_empty = client.get("/api/plans")
    assert res_empty.status_code == 200
    assert res_empty.json() == []

    # 2. Add two records with sequential timestamps
    plan1 = _sample_learning_plan("Plan 1")
    plan2 = _sample_learning_plan("Plan 2")

    rec1 = LearningPlanModel(
        title="Plan 1",
        goal="Goal 1",
        input_data={"durationDays": 5},
        plan_data=plan1.model_dump(mode="json"),
        created_at=datetime.datetime(2026, 10, 1, 10, 0, tzinfo=datetime.timezone.utc),
    )
    rec2 = LearningPlanModel(
        title="Plan 2",
        goal="Goal 2",
        input_data={"durationDays": 10},
        plan_data=plan2.model_dump(mode="json"),
        created_at=datetime.datetime(2026, 10, 2, 10, 0, tzinfo=datetime.timezone.utc),
    )
    db_session.add_all([rec1, rec2])
    db_session.commit()

    # 3. Fetch all: should be ordered newest first (rec2, then rec1)
    res = client.get("/api/plans")
    assert res.status_code == 200
    plans = res.json()
    assert len(plans) == 2
    assert plans[0]["title"] == "Plan 2"
    assert plans[1]["title"] == "Plan 1"
    assert plans[0]["durationDays"] == 10


def test_get_plan_by_id_success_and_not_found(client, db_session):
    """
    Verifies GET /api/plans/{plan_id} returns full plan details or 404 for missing IDs.
    """
    # 1. Missing ID returns 404
    res_missing = client.get("/api/plans/9999")
    assert res_missing.status_code == 404
    assert "not found" in res_missing.json()["detail"].lower()

    # 2. Existing record returns complete details
    plan = _sample_learning_plan("Complete Web Dev")
    rec = LearningPlanModel(
        title="Complete Web Dev",
        goal="Become full stack developer",
        input_data={"goal": "Become full stack developer", "durationDays": 14},
        plan_data=plan.model_dump(mode="json"),
        google_doc_url="https://docs.google.com/document/d/doc123/edit",
    )
    db_session.add(rec)
    db_session.commit()
    db_session.refresh(rec)

    res_found = client.get(f"/api/plans/{rec.id}")
    assert res_found.status_code == 200
    data = res_found.json()
    assert data["id"] == rec.id
    assert data["title"] == "Complete Web Dev"
    assert data["google_doc_url"] == "https://docs.google.com/document/d/doc123/edit"
    assert "plan_data" in data
    assert len(data["plan_data"]["days"]) == 2


def test_patch_plan_updates_in_place(client, db_session):
    """
    Verifies PATCH /api/plans/{plan_id} modifies an existing record in-place
    without creating duplicate records.
    """
    original_plan = _sample_learning_plan("Original Python Plan")
    rec = LearningPlanModel(
        title="Original Python Plan",
        goal="Learn Python",
        input_data={"durationDays": 2, "hoursPerDay": 2.0, "startDate": "2026-11-01"},
        plan_data=original_plan.model_dump(mode="json"),
    )
    db_session.add(rec)
    db_session.commit()
    db_session.refresh(rec)
    plan_id = rec.id

    revised_plan = _sample_learning_plan("Revised Python Plan (Hands-on Focus)")
    revised_result = PlanResult(
        feasible=True,
        feasibilityMessage="Revised to focus on projects.",
        estimatedRequiredHours=4.0,
        availableHours=4.0,
        recommendations=[],
        plan=revised_plan,
    )

    with patch("app.api.v1.plans.modify_learning_plan", return_value=revised_result):
        patch_payload = {
            "feedback": "Add more coding projects and practice exercises.",
        }
        res = client.patch(f"/api/plans/{plan_id}", json=patch_payload)
        assert res.status_code == 200
        resp_data = res.json()
        assert resp_data["planId"] == plan_id

        # Verify only 1 record exists in total (no duplicates)
        total_records = db_session.query(LearningPlanModel).count()
        assert total_records == 1

        # Verify updated content in database
        updated_rec = db_session.query(LearningPlanModel).filter(LearningPlanModel.id == plan_id).first()
        assert updated_rec.title == "Revised Python Plan (Hands-on Focus)"


def test_create_doc_saves_url_against_plan_record(client, db_session):
    """
    Verifies that when POST /api/plan/create-doc is called with plan_id,
    the generated document URL is automatically saved on the learning_plans record.
    """
    plan = _sample_learning_plan("Docs Test Plan")
    rec = LearningPlanModel(
        title="Docs Test Plan",
        goal="Test Google Doc Persistence",
        input_data={"durationDays": 2},
        plan_data=plan.model_dump(mode="json"),
        google_doc_url=None,
    )
    db_session.add(rec)
    db_session.commit()
    db_session.refresh(rec)
    plan_id = rec.id

    mock_doc_result = {
        "document_id": "google-doc-abc-123",
        "document_url": "https://docs.google.com/document/d/google-doc-abc-123/edit",
        "verified": True,
    }

    with patch("app.api.v1.plans.is_google_connected", return_value=True), \
         patch("app.api.v1.plans.create_google_doc_for_plan", return_value=mock_doc_result):
        
        doc_payload = {
            "plan": plan.model_dump(mode="json"),
            "plan_id": plan_id,
        }
        response = client.post("/api/plan/create-doc", json=doc_payload)
        assert response.status_code == 200
        assert response.json()["documentUrl"] == "https://docs.google.com/document/d/google-doc-abc-123/edit"

        # Verify database record now has the google_doc_url
        updated_rec = db_session.query(LearningPlanModel).filter(LearningPlanModel.id == plan_id).first()
        assert updated_rec.google_doc_url == "https://docs.google.com/document/d/google-doc-abc-123/edit"
