# ==============================================================================
# File: server/app/repositories/plan_repository.py
# Purpose: Repository encapsulating SQLAlchemy query and transaction logic for Learning Plans.
# ==============================================================================

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.learning_plan import LearningPlanModel

logger = logging.getLogger(__name__)


def create_learning_plan(
    db: Session,
    title: str,
    goal: str,
    input_data: Dict[str, Any],
    plan_data: Dict[str, Any],
    google_doc_url: Optional[str] = None,
) -> LearningPlanModel:
    """
    Creates and persists a new learning plan in PostgreSQL.
    Manages session transaction (add, commit, refresh) and rolls back on failure.
    """
    try:
        record = LearningPlanModel(
            title=title,
            goal=goal,
            input_data=input_data,
            plan_data=plan_data,
            google_doc_url=google_doc_url,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        logger.info("Persisted learning plan successfully with ID: %s", record.id)
        return record
    except Exception as exc:
        db.rollback()
        logger.error("Failed to persist learning plan to database: %s", exc)
        raise exc


def get_all_learning_plans(db: Session) -> List[LearningPlanModel]:
    """
    Retrieves all learning plans from the database ordered newest first (created_at DESC).
    """
    try:
        return (
            db.query(LearningPlanModel)
            .order_by(LearningPlanModel.created_at.desc())
            .all()
        )
    except Exception as exc:
        logger.error("Failed to retrieve learning plans: %s", exc)
        raise exc


def get_learning_plan_by_id(db: Session, plan_id: int) -> Optional[LearningPlanModel]:
    """
    Retrieves a single learning plan by its primary key ID.
    Returns None if no matching plan exists.
    """
    try:
        return (
            db.query(LearningPlanModel)
            .filter(LearningPlanModel.id == plan_id)
            .first()
        )
    except Exception as exc:
        logger.error("Failed to retrieve learning plan ID %s: %s", plan_id, exc)
        raise exc


def update_learning_plan(
    db: Session,
    plan_id: int,
    title: Optional[str] = None,
    plan_data: Optional[Dict[str, Any]] = None,
    input_data: Optional[Dict[str, Any]] = None,
    google_doc_url: Optional[str] = None,
) -> Optional[LearningPlanModel]:
    """
    Updates an existing learning plan record in-place.
    Only non-None arguments are updated.
    Returns the refreshed model or None if the record does not exist.
    """
    record = get_learning_plan_by_id(db, plan_id)
    if not record:
        return None

    try:
        if title is not None:
            record.title = title
        if plan_data is not None:
            record.plan_data = plan_data
        if input_data is not None:
            record.input_data = input_data
        if google_doc_url is not None:
            record.google_doc_url = google_doc_url

        db.commit()
        db.refresh(record)
        logger.info("Successfully updated learning plan ID %s in-place", plan_id)
        return record
    except Exception as exc:
        db.rollback()
        logger.error("Failed to update learning plan ID %s: %s", plan_id, exc)
        raise exc


def update_plan_google_doc_url(
    db: Session,
    plan_id: int,
    google_doc_url: str,
) -> Optional[LearningPlanModel]:
    """
    Updates the google_doc_url of an existing learning plan record.
    """
    return update_learning_plan(db, plan_id=plan_id, google_doc_url=google_doc_url)

