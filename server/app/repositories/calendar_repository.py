# ==============================================================================
# File: server/app/repositories/calendar_repository.py
# Purpose: Repository for managing Google Calendar event mappings and persistence.
# ==============================================================================

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.learning_plan import LearningPlanModel

logger = logging.getLogger(__name__)


def save_calendar_event_mappings(
    db: Session,
    plan_id: int,
    events: List[Dict[str, Any]],
) -> Optional[LearningPlanModel]:
    """
    Saves Google Calendar event mappings for a learning plan.
    Currently maps event metadata into the plan's JSONB plan_data.
    If a dedicated calendar_events table is added in the future,
    this function encapsulates that migration without changing API routes.
    """
    try:
        record = (
            db.query(LearningPlanModel)
            .filter(LearningPlanModel.id == plan_id)
            .first()
        )
        if not record:
            logger.warning("Cannot save calendar mappings: plan ID %s not found", plan_id)
            return None

        # Store calendar events in JSONB plan_data
        updated_plan_data = dict(record.plan_data) if isinstance(record.plan_data, dict) else {}
        updated_plan_data["calendar_events"] = events
        record.plan_data = updated_plan_data

        db.commit()
        db.refresh(record)
        logger.info("Saved %s calendar event mappings for plan ID %s", len(events), plan_id)
        return record
    except Exception as exc:
        db.rollback()
        logger.error("Failed to save calendar event mappings for plan ID %s: %s", plan_id, exc)
        raise exc


def get_calendar_event_mappings(
    db: Session,
    plan_id: int,
) -> List[Dict[str, Any]]:
    """
    Retrieves Google Calendar event mappings for a specific learning plan.
    Returns an empty list if the plan has no scheduled calendar events.
    """
    try:
        record = (
            db.query(LearningPlanModel)
            .filter(LearningPlanModel.id == plan_id)
            .first()
        )
        if not record or not isinstance(record.plan_data, dict):
            return []

        return record.plan_data.get("calendar_events", [])
    except Exception as exc:
        logger.error("Failed to retrieve calendar mappings for plan ID %s: %s", plan_id, exc)
        raise exc

