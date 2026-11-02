# ==============================================================================
# File: server/app/api/v1/plans.py
# Purpose: API router for learning plan generation, persistence, modification, and Google Docs export.
# ==============================================================================

import datetime
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories.plan_repository import (
    create_learning_plan,
    get_all_learning_plans,
    get_learning_plan_by_id,
    update_learning_plan,
    update_plan_google_doc_url,
)
from app.schemas.plan import (
    PlanRequest,
    PlanResponse,
    PlanModifyRequest,
    LearningPlan,
    SavedPlanSummary,
    SavedPlanDetail,
    PlanPatchRequest,
    DocCreateRequest,
    DocCreateResponse,
)
from app.services.llm import generate_learning_plan, modify_learning_plan
from app.services.oauth import is_google_connected
from app.services.google_docs import create_google_doc_for_plan

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Plans"])


@router.post(
    "/plan",
    response_model=PlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate AI Learning Plan or Feasibility Assessment",
)
def submit_plan_request(
    request: PlanRequest,
    db: Session = Depends(get_db),
) -> PlanResponse:
    """
    Receives the user's learning goal and constraints, invokes Google Gemini
    to assess schedule feasibility, and generates a structured curriculum.
    Automatically saves valid, feasible plans to PostgreSQL via repository.
    """
    try:
        plan_result = generate_learning_plan(request)
        
        saved_id: Optional[int] = None
        # Auto-save feasible, validated plans into PostgreSQL
        if plan_result.feasible and plan_result.plan:
            try:
                record = create_learning_plan(
                    db=db,
                    title=plan_result.plan.title,
                    goal=request.goal,
                    input_data=request.model_dump(mode="json"),
                    plan_data=plan_result.plan.model_dump(mode="json"),
                )
                saved_id = record.id
                logger.info("Automatically saved generated plan to database with ID: %s", saved_id)
            except Exception as db_exc:
                logger.error("Failed to persist generated plan to database: %s", db_exc)

        message = (
            "Learning plan generated successfully"
            if plan_result.feasible
            else "Learning plan feasibility assessment completed"
        )
        
        return PlanResponse(
            message=message,
            data=plan_result,
            plan_id=saved_id,
            planId=saved_id,
        )

    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except RuntimeError as run_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI Service Error: {str(run_err)}",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating the learning plan.",
        )


@router.post(
    "/plan/modify",
    response_model=PlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Modify an Existing AI Learning Plan Based on User Feedback",
)
def modify_plan_request(request: PlanModifyRequest) -> PlanResponse:
    """
    Receives the current learning plan and user feedback, asks Gemini to
    produce a modified version that preserves the original schedule constraints
    (duration, start date, daily hours) while applying the requested changes.
    """
    try:
        plan_result = modify_learning_plan(request)
        return PlanResponse(
            message="Learning plan modified successfully",
            data=plan_result,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except RuntimeError as run_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI Service Error: {str(run_err)}",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while modifying the learning plan.",
        )


@router.get(
    "/plans",
    response_model=List[SavedPlanSummary],
    status_code=status.HTTP_200_OK,
    summary="Retrieve all saved learning plans (newest first)",
)
def get_all_plans(db: Session = Depends(get_db)) -> List[SavedPlanSummary]:
    """
    Retrieves all saved learning plans ordered by creation date descending (newest first).
    """
    try:
        records = get_all_learning_plans(db)
        return [SavedPlanSummary(**r.to_summary_dict()) for r in records]
    except Exception as exc:
        logger.error("Database error fetching plans: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while retrieving saved learning plans.",
        )


@router.get(
    "/plans/{plan_id}",
    response_model=SavedPlanDetail,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a specific learning plan by ID",
)
def get_plan_by_id(plan_id: int, db: Session = Depends(get_db)) -> SavedPlanDetail:
    """
    Retrieves one learning plan with full details by primary key ID.
    Raises 404 if the record does not exist.
    """
    try:
        record = get_learning_plan_by_id(db, plan_id)
    except Exception as exc:
        logger.error("Database error looking up plan %s: %s", plan_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while retrieving plan details.",
        )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Learning plan with ID {plan_id} not found.",
        )

    return SavedPlanDetail(**record.to_detail_dict())


@router.patch(
    "/plans/{plan_id}",
    response_model=PlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Modify and update an existing learning plan in-place",
)
def patch_plan_by_id(
    plan_id: int,
    patch_req: PlanPatchRequest,
    db: Session = Depends(get_db),
) -> PlanResponse:
    """
    Modifies an existing plan record in-place based on user feedback.
    Reuses existing modify_learning_plan and validation logic.
    Updates the database record via repository rather than creating a duplicate.
    """
    try:
        record = get_learning_plan_by_id(db, plan_id)
    except Exception as exc:
        logger.error("Database error looking up plan %s for modification: %s", plan_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while accessing plan for modification.",
        )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Learning plan with ID {plan_id} not found.",
        )

    # Reconstruct currentPlan and schedule constraints
    current_plan_data = patch_req.currentPlan or LearningPlan(**record.plan_data)
    input_data = record.input_data if isinstance(record.input_data, dict) else {}
    duration_days = (
        patch_req.durationDays
        or input_data.get("durationDays")
        or len(current_plan_data.days)
    )
    hours_per_day = (
        patch_req.hoursPerDay
        or input_data.get("hoursPerDay")
        or (current_plan_data.days[0].estimatedHours if current_plan_data.days else 2.0)
    )
    start_date_val = patch_req.startDate
    if not start_date_val:
        raw_start = input_data.get("startDate")
        if raw_start:
            if isinstance(raw_start, str):
                start_date_val = datetime.date.fromisoformat(raw_start)
            elif isinstance(raw_start, datetime.date):
                start_date_val = raw_start
        elif current_plan_data.days:
            start_date_val = current_plan_data.days[0].date
        else:
            start_date_val = datetime.date.today()

    modify_request = PlanModifyRequest(
        currentPlan=current_plan_data,
        feedback=patch_req.feedback,
        durationDays=duration_days,
        hoursPerDay=hours_per_day,
        startDate=start_date_val,
    )

    try:
        plan_result = modify_learning_plan(modify_request)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except RuntimeError as run_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI Service Error: {str(run_err)}",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while modifying the learning plan.",
        )

    # Update the existing database record in-place via repository
    if plan_result.plan:
        try:
            updated_input = None
            if isinstance(record.input_data, dict):
                updated_input = dict(record.input_data)
                updated_input["durationDays"] = duration_days
                updated_input["hoursPerDay"] = hours_per_day
                updated_input["startDate"] = str(start_date_val)

            record = update_learning_plan(
                db=db,
                plan_id=plan_id,
                title=plan_result.plan.title,
                plan_data=plan_result.plan.model_dump(mode="json"),
                input_data=updated_input,
            )
        except Exception as db_exc:
            logger.error("Failed to update plan record %s in database: %s", plan_id, db_exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error while saving modified plan.",
            )

    return PlanResponse(
        message="Learning plan modified and updated successfully",
        data=plan_result,
        plan_id=record.id,
        planId=record.id,
    )


@router.post(
    "/plan/create-doc",
    response_model=DocCreateResponse,
    status_code=status.HTTP_200_OK,
    summary="Create Google Doc for Approved Learning Plan",
)
def api_create_google_doc(
    request: DocCreateRequest,
    db: Session = Depends(get_db),
) -> DocCreateResponse:
    """
    Receives an approved LearningPlan and creates a formatted Google Doc.
    If request.plan_id is provided, automatically saves the document URL against the database record.
    """
    # 1. Reject if Google account is not connected
    if not is_google_connected():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account is not connected. Please connect your Google account before creating a Google Doc.",
        )

    # 2. Invoke Google Docs creation service module
    try:
        result = create_google_doc_for_plan(request.plan)
        doc_url = result.get("document_url")

        # Save Google Docs URL against plan record if plan_id is provided
        if request.plan_id and doc_url:
            try:
                update_plan_google_doc_url(db, request.plan_id, doc_url)
                logger.info("Saved Google Doc URL against plan ID %s", request.plan_id)
            except Exception as db_err:
                logger.error("Failed to associate Google Doc URL with plan ID %s: %s", request.plan_id, db_err)

        if not result["verified"]:
            return DocCreateResponse(
                message=result.get("error") or f"Google Doc was created ({result['document_id']}), but PathAI could not verify it.",
                documentId=result["document_id"],
                documentUrl=result["document_url"],
                verified=False,
            )

        return DocCreateResponse(
            message="Google Doc created and verified successfully",
            documentId=result["document_id"],
            documentUrl=result["document_url"],
            verified=True,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except RuntimeError as run_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(run_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while creating the Google Doc: {str(exc)}",
        )
