"""
InkFlow Timed Drill and Genome Extraction API Routes.

================================================================================
Architecture and Design Rationale:
--------------------------------------------------------------------------------
This module provides endpoints for the 60-second timed onboarding drill
adhering strictly to C:/InkFlow/docs/backend.md Section 8:

Endpoints:
- `GET /api/v1/grill/prompts`:
  Returns 3 unlabelled situational scenarios for the 60-second timed drill.
- `POST /api/v1/grill/analyze`:
  Ingests the 3 raw drill responses, computes initial StyleGenome, and saves to MongoDB.
================================================================================
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.models.genome import StyleGenomeResponse
from app.services.grill import grill_service

logger = logging.getLogger("inkflow.api.grill")
router = APIRouter()


class DrillAnswer(BaseModel):
    """Single answer to a timed drill scenario prompt."""
    question_id: Optional[str] = Field(None, description="Scenario identifier (scenario_1, etc.).")
    id: Optional[str] = Field(None, description="Alternative prompt ID.")
    text: str = Field(..., min_length=3, description="Author's rapid unvarnished response.")

    def get_id(self) -> str:
        return self.question_id or self.id or "q"


class DrillAnalyzeRequest(BaseModel):
    """Payload containing responses to the 3 timed onboarding drill scenarios."""
    answers: List[DrillAnswer] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Collection of timed drill responses.",
    )


@router.get(
    "/prompts",
    response_model=List[Dict[str, Any]],
    summary="Get 3 unlabelled situational scenarios for 60-second timed drill",
)
async def get_grill_prompts(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """
    GET /api/v1/grill/prompts:
    Returns 3 unlabelled situational scenarios for the 60-second timed drill.
    Contract specified in docs/backend.md Section 8.
    """
    return grill_service.get_timed_prompts(count=3)


@router.get("/questions", response_model=List[Dict[str, Any]], include_in_schema=False)
async def get_drill_questions(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Backward-compatible alias for /prompts."""
    return grill_service.get_timed_prompts(count=3)


@router.post(
    "/analyze",
    response_model=StyleGenomeResponse,
    summary="Analyze drill responses, compute initial StyleGenome, and save to MongoDB",
)
async def analyze_drill(
    payload: DrillAnalyzeRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> StyleGenomeResponse:
    """
    POST /api/v1/grill/analyze:
    Ingests the 3 raw drill responses, computes initial StyleGenome, and saves to MongoDB.
    Contract specified in docs/backend.md Section 8.
    """
    user_id = str(current_user.get("_id", current_user.get("userId", "")))
    answers_dicts = [{"question_id": a.get_id(), "text": a.text} for a in payload.answers]

    try:
        genome_doc = await grill_service.process_drill_submission(
            user_id=user_id,
            answers=answers_dicts,
        )
        return StyleGenomeResponse(**genome_doc)
    except Exception as exc:
        logger.error("Failed to analyze drill submission: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calibrate Style Genome: {str(exc)}",
        )


@router.post("/submit", response_model=StyleGenomeResponse, include_in_schema=False)
async def submit_drill(
    payload: DrillAnalyzeRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> StyleGenomeResponse:
    """Backward-compatible alias for /analyze."""
    return await analyze_drill(payload, current_user)
