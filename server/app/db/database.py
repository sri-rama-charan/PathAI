# ==============================================================================
# File: server/app/db/database.py
# Purpose: SQLAlchemy database engine, session management, and table initialization.
# ==============================================================================

import logging
from typing import Generator
from sqlalchemy import create_engine, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import get_database_url

logger = logging.getLogger(__name__)

Base = declarative_base()

# JSONB on PostgreSQL (Neon / Render), JSON on SQLite for portable testing
JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


def create_db_engine():
    """
    Creates the SQLAlchemy Engine with Neon / PostgreSQL pooling optimizations.
    """
    db_url = get_database_url()
    if db_url.startswith("sqlite"):
        return create_engine(
            db_url,
            connect_args={"check_same_thread": False},
        )

    # Neon Serverless Postgres recommendations:
    # pool_pre_ping=True handles compute scale-to-zero wakeups transparently
    return create_engine(
        db_url,
        pool_pre_ping=True,
        pool_recycle=300,
    )


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a SQLAlchemy session per request.
    Closes the session after the request lifecycle completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Creates all declared database tables if they do not exist.
    """
    # Import models here so Base knows about them before create_all
    import app.models.learning_plan  # noqa: F401

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
    except Exception as exc:
        logger.error("Failed to initialize database tables: %s", exc)
        raise

