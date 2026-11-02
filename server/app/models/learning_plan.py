# ==============================================================================
# File: server/app/models/learning_plan.py
# Purpose: SQLAlchemy ORM models for PathAI PostgreSQL database.
# ==============================================================================

import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.db.database import Base, JSON_TYPE


class LearningPlanModel(Base):
    """
    SQLAlchemy ORM model for storing generated and user-modified learning plans.
    Persists original request parameters and generated structured curriculum.
    """
    __tablename__ = "learning_plans"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    goal = Column(Text, nullable=False)
    input_data = Column(JSON_TYPE, nullable=False)
    plan_data = Column(JSON_TYPE, nullable=False)
    google_doc_url = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    def to_summary_dict(self) -> dict:
        """
        Returns lightweight summary dictionary for My Plans dashboard list view.
        """
        duration = None
        if isinstance(self.input_data, dict):
            duration = self.input_data.get("durationDays")
        elif isinstance(self.plan_data, dict) and "days" in self.plan_data:
            duration = len(self.plan_data["days"])

        return {
            "id": self.id,
            "title": self.title,
            "goal": self.goal,
            "durationDays": duration,
            "google_doc_url": self.google_doc_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_detail_dict(self) -> dict:
        """
        Returns full detailed dictionary for plan details view.
        """
        return {
            "id": self.id,
            "title": self.title,
            "goal": self.goal,
            "input_data": self.input_data,
            "plan_data": self.plan_data,
            "google_doc_url": self.google_doc_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

