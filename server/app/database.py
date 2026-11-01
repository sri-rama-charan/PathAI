# ==============================================================================
# File: server/app/database.py
# Purpose: SQLAlchemy database engine, session management, and table initialization.
# ==============================================================================

import os
import logging
from pathlib import Path
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, sessionmaker, Session

logger = logging.getLogger(__name__)

# Resolve path to server directory and load environment variables
SERVER_DIR = Path(__file__).resolve().parent.parent
load_dotenv(SERVER_DIR / ".env", override=True)
load_dotenv(override=True)

Base = declarative_base()

# JSONB on PostgreSQL, JSON on SQLite for portable testing
JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


def get_database_url() -> str:
    """
    Retrieves and normalizes DATABASE_URL from environment variables.
    Handles Render's 'postgres://' prefix by converting to 'postgresql://'.
    Falls back to a local SQLite database for development/testing if unset.
    """
    raw_url = os.getenv("DATABASE_URL", "").strip()
    if not raw_url:
        db_path = SERVER_DIR / "pathai.db"
        logger.info("DATABASE_URL not set. Falling back to local SQLite: %s", db_path)
        return f"sqlite:///{db_path}"

    # Render uses postgres:// which SQLAlchemy 1.4+ / 2.0 deprecated
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)

    return raw_url


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
    import app.models  # noqa: F401

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
    except Exception as exc:
        logger.error("Failed to initialize database tables: %s", exc)
        raise
