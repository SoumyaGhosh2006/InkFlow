"""
InkFlow Rewrite Pipeline and Adaptive Feedback API Routes.

================================================================================
Architecture and Design Rationale:
--------------------------------------------------------------------------------
This module provides the primary transformation and feedback endpoints for InkFlow
adhering strictly to C:/InkFlow/docs/backend.md Section 8:

Endpoints:
1. `POST /api/v1/rewrite/pipeline`:
   - Gated by in-flight lazy weekly quota enforcement (2,500 word limit for Free tier).
   - If quota exceeded, returns HTTP 403 Forbidden with QUOTA_EXCEEDED payload.
   - Executes 4-stage sequential pipeline with reason-aware retry and soft warning fallback.
   - Increments wordsUsedThisWeek in MongoDB on success.
   - Returns `{ finalOutput, meaningCheckFailed, meaningWarning, provider, evalScores }`.
2. `POST /api/v1/rewrite/accept`:
   - Receives `{ rewriteId, finalUserText }`.
   - Genome Integrity Protection: If meaningCheckFailed was True, saves accepted record
     for history but EXPLICITLY SKIPS the adaptive learning loop.
   - Otherwise computes stylistic delta and evaluates the 5-10 session recurrence threshold.
================================================================================
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from bson import ObjectId

from app.core.database import get_genomes_collection, get_rewrites_collection
from app.core.security import get_current_user
from app.models.rewrite import (
    RewriteRequest,
    RewriteResponse,
    RewriteAcceptRequest,
)
from app.services.quota import check_and_apply_quota, count_words
from app.services.pipeline import rewrite_pipeline_service
from app.services.adaptive import adaptive_learning_service
from app.services.providers import resilient_llm_service

logger = logging.getLogger("inkflow.api.rewrite")
router = APIRouter()


class RewriteFeedbackRequest(BaseModel):
    """Backward-compatible feedback request payload."""
    rewrite_id: Optional[str] = Field(None, description="Identifier of the rewrite record.")
    rewriteId: Optional[str] = Field(None, description="Alternative rewriteId field.")
    session_id: Optional[str] = Field(None, description="Editing session identifier.")
    generated_text: Optional[str] = Field(None, description="Original output text.")
    final_text: Optional[str] = Field(None, description="Accepted text.")
    finalUserText: Optional[str] = Field(None, description="Accepted text alias.")

    def get_rewrite_id(self) -> str:
        return self.rewriteId or self.rewrite_id or ""

    def get_final_text(self) -> str:
        return self.finalUserText or self.final_text or ""


@router.post(
    "/pipeline",
    response_model=RewriteResponse,
    summary="Execute the 4-stage anti-slop rewrite pipeline",
)
async def execute_rewrite_pipeline(
    payload: RewriteRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> RewriteResponse:
    """
    POST /api/v1/rewrite/pipeline:
    Executes the 4-stage sequential quality pipeline anchored to user's Style Genome.
    Contract defined in docs/backend.md Section 8.
    """
    user_id = str(current_user.get("_id", current_user.get("userId", "")))
    raw_text = payload.get_raw_input()

    if not raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Draft text must not be empty.",
        )

    # --------------------------------------------------------------------------
    # Step 1: Enforce in-flight lazy quota reset and word consumption gate
    # Returns HTTP 403 Forbidden (QUOTA_EXCEEDED) if allocation is exhausted.
    # --------------------------------------------------------------------------
    updated_user, words_consumed, quota_remaining = await check_and_apply_quota(
        user_id=user_id,
        incoming_text=raw_text,
    )

    # --------------------------------------------------------------------------
    # Step 2: Retrieve author's Style Genome (or establish default baseline)
    # --------------------------------------------------------------------------
    genomes_col = get_genomes_collection()
    genome = await genomes_col.find_one({"$or": [{"userId": user_id}, {"user_id": user_id}]})

    if not genome:
        logger.info("No Style Genome found for user %s; using calibrated default baseline.", user_id)
        genome = {
            "userId": user_id,
            "version": 1,
            "baselineGenome": {
                "avgSentenceLength": 13.8,
                "sentenceLengthVariance": 7.4,
                "formalityScore": 6.8,
                "vocabularyRichnessTTR": 0.65,
                "transitionHabits": ["basically", "at the end of the day", "look,"],
                "punctuationHabits": {
                    "commaFrequency": "moderate",
                    "emDashUsage": "rare",
                    "parenthesesUsage": "frequent",
                },
            },
            "contextProfiles": {
                "work_formal": {"formalityOffset": 1.5},
                "academic_educator": {"formalityOffset": 1.0},
                "workplace_chat": {"formalityOffset": -1.0},
            },
            "exemplars": [],
            "recentEditsBuffer": [],
            "recurrent_patterns": [],
        }

    # --------------------------------------------------------------------------
    # Step 3: Execute the 4-Stage Sequential Rewrite Pipeline
    # --------------------------------------------------------------------------
    try:
        response: RewriteResponse = await rewrite_pipeline_service.execute(
            request=payload,
            genome=genome,
            words_consumed=words_consumed,
            quota_remaining=quota_remaining,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Pipeline failure for user %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rewrite transformation failed: {str(exc)}",
        )

    # --------------------------------------------------------------------------
    # Step 4: Persist Rewrite Record in MongoDB History Collection
    # --------------------------------------------------------------------------
    now_utc = datetime.now(timezone.utc)
    try:
        rewrites_col = get_rewrites_collection()
        record = {
            "userId": user_id,
            "user_id": user_id,
            "context": payload.get_context(),
            "originalInput": raw_text,
            "stageOutputs": response.stageOutputs.model_dump() if response.stageOutputs else {},
            "finalOutput": response.finalOutput,
            "meaningCheckFailed": response.meaningCheckFailed,
            "meaningWarning": response.meaningWarning,
            "userEdited": False,
            "acceptedAt": None,
            "provider": response.provider,
            "evalScores": response.evalScores.model_dump(),
            "words_consumed": words_consumed,
            "created_at": now_utc,
        }
        insert_res = await rewrites_col.insert_one(record)
        response.rewrite_id = str(insert_res.inserted_id)
    except Exception as exc:
        logger.warning("Failed to persist rewrite record: %s", exc)

    return response


@router.post("", response_model=RewriteResponse, include_in_schema=False)
async def execute_rewrite_default(
    payload: RewriteRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> RewriteResponse:
    """Backward-compatible alias for /pipeline."""
    return await execute_rewrite_pipeline(payload, current_user)


@router.post(
    "/accept",
    summary="Record accepted text with Genome Integrity Protection",
)
async def accept_rewrite(
    payload: RewriteAcceptRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    POST /api/v1/rewrite/accept:
    Records accepted rewrite text.
    Genome Integrity Protection: If the rewrite had meaningCheckFailed: true,
    saves accepted record for history but EXPLICITLY SKIPS the adaptive learning loop.
    Contract specified in docs/backend.md Section 8.
    """
    user_id = str(current_user.get("_id", current_user.get("userId", "")))
    result = await adaptive_learning_service.process_accepted_rewrite(
        user_id=user_id,
        rewrite_id=payload.rewriteId,
        final_user_text=payload.finalUserText,
    )

    # Mark rewrite record as userEdited and accepted in MongoDB
    try:
        rewrites_col = get_rewrites_collection()
        await rewrites_col.update_one(
            {"_id": ObjectId(payload.rewriteId)},
            {
                "$set": {
                    "finalOutput": payload.finalUserText,
                    "userEdited": True,
                    "acceptedAt": datetime.now(timezone.utc),
                }
            },
        )
    except Exception as exc:
        logger.warning("Could not update rewrite accept timestamp: %s", exc)

    return {
        "status": "success",
        "details": result,
    }


@router.post("/feedback", include_in_schema=False)
async def submit_rewrite_feedback(
    payload: RewriteFeedbackRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Backward-compatible alias for /accept."""
    user_id = str(current_user.get("_id", current_user.get("userId", "")))
    rewrite_id = payload.get_rewrite_id()
    final_text = payload.get_final_text()

    if rewrite_id:
        result = await adaptive_learning_service.process_accepted_rewrite(
            user_id=user_id,
            rewrite_id=rewrite_id,
            final_user_text=final_text,
            session_id=payload.session_id,
        )
        return {"status": "success", "details": result}

    promoted = await adaptive_learning_service.record_session_diff(
        user_id=user_id,
        session_id=payload.session_id or "session_default",
        generated_text=payload.generated_text or "",
        user_edited_text=final_text,
    )
    return {
        "status": "success",
        "patterns_promoted": promoted,
        "message": f"Recorded feedback. {len(promoted)} pattern(s) reached promotion threshold.",
    }


class ChatMessage(BaseModel):
    role: str = Field(default="user", description="'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message content")


class ChatComposeRequest(BaseModel):
    prompt: Optional[str] = Field(None, description="Direct draft prompt or task")
    messages: Optional[List[ChatMessage]] = Field(default=None, description="Full multi-turn chat history")
    context: Optional[str] = Field(default="work_formal", description="Context profile: work_formal, workplace_chat, academic, etc.")
    tone: Optional[str] = Field(default=None, description="Tone guidance, e.g. 'direct', 'crisp', 'warm'")


class ChatComposeResponse(BaseModel):
    reply: str
    words_consumed: int
    quota_remaining: int
    provider: str


@router.post(
    "/chat",
    response_model=ChatComposeResponse,
    summary="Direct multi-turn AI Writer chatbox for drafting emails, notes, letters, and text directly",
)
async def chat_compose(
    payload: ChatComposeRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> ChatComposeResponse:
    """
    POST /api/v1/rewrite/chat:
    Direct AI generation chatbox. Crafts complete emails, lecture notes, messages,
    and documents directly in natural cadence using the configured Groq LLM.
    """
    user_id = str(current_user.get("_id", current_user.get("userId", "")))

    prompt_text = payload.prompt or ""
    if not prompt_text and payload.messages:
        prompt_text = payload.messages[-1].content

    words_in_prompt = max(1, count_words(prompt_text))
    updated_user, words_consumed, remaining_quota = await check_and_apply_quota(
        user_id, prompt_text or "chat compose prompt"
    )

    # Style Genome context integration
    exemplars = []
    try:
        genomes_col = get_genomes_collection()
        user_genome = await genomes_col.find_one({"$or": [{"userId": user_id}, {"user_id": user_id}]})
        if user_genome:
            exemplars = user_genome.get("exemplars", [])
    except Exception:
        pass

    system_instruction = (
        "You are InkFlow AI Writer, an authentic, high-precision composition assistant.\n"
        "Draft complete, ready-to-use text (emails, letters, study notes, messages, articles, announcements) directly in natural, human cadence.\n\n"
        "STRICT COMPOSITION RULES:\n"
        "1. NEVER use AI cliches or generic slop (e.g. 'delve', 'testament', 'tapestry', 'it is important to note', 'in conclusion', 'beacon', 'moreover', 'pivotal').\n"
        "2. Write with organic rhythm, varied sentence lengths, and genuine human pacing.\n"
        "3. If drafting an email, format complete with a clear 'Subject:' line and polished message body.\n"
        "4. If drafting notes, use clear readable headings and concise bullet points.\n"
        "5. If drafting a message/SMS, be concise, direct, and conversational.\n"
        f"6. Context profile: {payload.context}. Tone guidance: {payload.tone or 'natural and direct'}."
    )
    if exemplars:
        system_instruction += "\nAuthor's authentic voice exemplars:\n" + "\n".join(f"- {ex}" for ex in exemplars[:2])

    chat_history: List[Dict[str, str]] = [{"role": "system", "content": system_instruction}]

    if payload.messages and len(payload.messages) > 0:
        for msg in payload.messages:
            chat_history.append({"role": msg.role, "content": msg.content})
    else:
        chat_history.append({"role": "user", "content": prompt_text})

    llm_result = await resilient_llm_service.complete(
        messages=chat_history,
        temperature=0.7,
        max_tokens=1500,
    )

    return ChatComposeResponse(
        reply=llm_result.text,
        words_consumed=words_consumed,
        quota_remaining=remaining_quota,
        provider=llm_result.provider,
    )
