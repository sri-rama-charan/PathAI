# ==============================================================================
# File: server/app/schemas.py
# Purpose: Pydantic schemas (blueprints) for validating request and response data.
#
# What this file does:
# 1. PlanRequest: Validates incoming POST /api/plan requests from the frontend.
#    - Checks types, required fields, positive numbers, non-empty strings, and valid dates.
# 2. PlanResponse: Defines the structure of the confirmation response.
#
# Why Pydantic is used here:
# Instead of writing dozens of manual 'if/else' checks for every single field,
# Pydantic automatically checks types, strips whitespaces, parses dates, and
# returns clear error messages if anything is wrong.
# ==============================================================================

from datetime import date
from typing import List
from pydantic import BaseModel, Field, field_validator, AliasChoices


class PlanRequest(BaseModel):
    """
    Request schema for creating a learning plan configuration.
    
    Attributes:
        goal: Target skill or subject to master (non-empty).
        experience: Current knowledge level and background (non-empty).
        durationDays: Total days available for the plan (positive integer, max 365).
        hoursPerDay: Daily study time in hours (positive float/int, max 24).
        startDate: Starting calendar date (YYYY-MM-DD).
        resourcePreferences: Optional list of preferred resource types (videos, docs, etc.).
    """
    goal: str = Field(
        ...,
        min_length=1,
        description="The primary skill or subject the user wants to learn.",
        examples=["Learn RAG with LangChain"],
    )
    experience: str = Field(
        ...,
        min_length=1,
        description="The user's existing technical knowledge or experience level.",
        examples=["Learned python basics, familiar with linear regression"],
    )
    durationDays: int = Field(
        ...,
        gt=0,
        le=365,
        description="Total duration in days (must be greater than 0).",
        examples=[30],
    )
    hoursPerDay: float = Field(
        ...,
        gt=0.0,
        le=24.0,
        description="Dedicated study hours per day (must be greater than 0).",
        examples=[2.0],
    )
    startDate: date = Field(
        ...,
        description="Target start date in YYYY-MM-DD format.",
        examples=["2026-09-11"],
    )
    resourcePreferences: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("resourcePreferences", "preferences"),
        description="Optional list of preferred resource types (e.g. videos, courses).",
        examples=[["videos", "documentation", "courses", "projects"]],
    )

    # --------------------------------------------------------------------------
    # Field Validators
    # --------------------------------------------------------------------------
    @field_validator("goal", "experience")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        """
        Ensures that string fields are not just blank spaces (e.g. '   ').
        """
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty or contain only whitespace.")
        return cleaned


class PlanResponse(BaseModel):
    """
    Response schema returned to the client after validating the learning plan request.
    """
    message: str = Field(
        ...,
        description="Human-readable status message confirming request receipt.",
        examples=["Learning plan request received successfully"],
    )
    data: PlanRequest = Field(
        ...,
        description="The validated learning plan configuration.",
    )
