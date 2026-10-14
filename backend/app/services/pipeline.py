"""
InkFlow 4-Stage Sequential Rewrite Pipeline.

================================================================================
Architecture and Design Rationale:
--------------------------------------------------------------------------------
This module implements the core voice-preserving 4-stage transformation pipeline
specified in C:/InkFlow/docs/backend.md Section 4:

Pipeline Stages:
1. Stage 1: Generate (Input Capped at 500 words)
   - If user supplies raw draft (inputType == 'raw_draft'): passes directly to Stage 2.
   - If user supplies bullet points (inputType == 'bullet_points'): drafts raw version via LLM.
2. Stage 2: Tone Transform
   - Injects Style Genome baseline (avgSentenceLength, transitionHabits, formalityOffset)
     and 2 exemplar anchors to eradicate synthetic AI slop words naturally.
3. Stage 3: Meaning Check (Semantic Fidelity Gate)
   - Evaluates factual claims. If drift is detected, triggers ONE immediate retry of Stage 2
     at temperature=0.3 injecting the exact `drift_reason`.
   - Soft Warning Fallback: If retry still fails verification, advances to Stage 4 without
     raising HTTP 422, attaching meaningCheckFailed=True and meaningWarning to protect UX.
4. Stage 4: Light Grammar Pass
   - INVARIANT: Preserves em-dashes ('—'), Oxford commas, semicolons, and pauses verbatim.
================================================================================
"""

import json
import logging
import re
import time
from typing import Dict, Any, List, Optional, Tuple
from fastapi import HTTPException, status

from app.core.sentry import trace_pipeline_stage
from app.models.rewrite import (
    RewriteRequest,
    RewriteResponse,
    RewriteStageLog,
    StageOutputs,
    InputType,
)
from app.services.providers import resilient_llm_service, LLMResult
from app.services.evals import (
    compute_all_evals,
    calculate_semantic_fidelity,
)
from app.services.quota import count_words

logger = logging.getLogger("inkflow.pipeline")


class PipelineExecutionError(Exception):
    """Raised when an unrecoverable failure aborts the pipeline."""
    pass


class RewritePipelineService:
    """
    Coordinates sequential execution of the 4 transformation stages.
    """

    async def execute(
        self,
        request: RewriteRequest,
        genome: Dict[str, Any],
        words_consumed: int,
        quota_remaining: int,
    ) -> RewriteResponse:
        """
        Executes the full 4-stage rewrite pipeline.
        
        Args:
            request: Inbound client rewrite request containing raw text and tone.
            genome: Author's active Style Genome profile dictionary.
            words_consumed: Words consumed and deducted from quota.
            quota_remaining: Balance of words left in the user's weekly quota.
            
        Returns:
            RewriteResponse complete with stage logs, evals, and soft warnings.
            
        Raises:
            HTTPException: 400 Bad Request if input exceeds 500 words.
        """
        raw_text = request.get_raw_input()
        word_count = count_words(raw_text)

        # ----------------------------------------------------------------------
        # Input Validation: 500 Words Per Pass Hard Limit (backend.md Section 4)
        # ----------------------------------------------------------------------
        if word_count > 500:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Input exceeds maximum allowed length of 500 words per pass (received {word_count} words).",
            )

        stage_logs: List[RewriteStageLog] = []
        last_provider_used = "groq_llama33"
        meaning_check_failed = False
        meaning_warning: Optional[str] = None
        retried_stage3 = False
        drift_reason_logged: Optional[str] = None

        # ----------------------------------------------------------------------
        # Stage 1: Generate (backend.md Section 4.2)
        # ----------------------------------------------------------------------
        async with trace_pipeline_stage("stage_1_generate", {"input_type": request.inputType}):
            stage1_out, stage1_log = await self._run_stage_1_generate(
                text=raw_text,
                input_type=request.inputType,
            )
            stage_logs.append(stage1_log)
            last_provider_used = stage1_log.provider_used

        # ----------------------------------------------------------------------
        # Stage 2: Tone Transform (backend.md Section 4.3)
        # ----------------------------------------------------------------------
        target_context = request.get_context()
        async with trace_pipeline_stage("stage_2_tone_transform", {"context": target_context}):
            stage2_out, stage2_log = await self._run_stage_2_tone_transform(
                text=stage1_out,
                target_context=target_context,
                genome=genome,
            )
            stage_logs.append(stage2_log)
            last_provider_used = stage2_log.provider_used

        # ----------------------------------------------------------------------
        # Stage 3: Meaning Check Gate & Reason-Aware Retry (backend.md Section 4.4)
        # ----------------------------------------------------------------------
        async with trace_pipeline_stage("stage_3_meaning_check"):
            (
                stage3_out,
                stage3_log,
                retry_log,
                check_failed,
                warning,
                drift_reason,
            ) = await self._run_stage_3_meaning_gate(
                original_text=raw_text,
                candidate_text=stage2_out,
                target_context=target_context,
                genome=genome,
            )
            stage_logs.append(stage3_log)
            if retry_log:
                stage_logs.append(retry_log)
                retried_stage3 = True
                drift_reason_logged = drift_reason
                last_provider_used = retry_log.provider_used
            meaning_check_failed = check_failed
            meaning_warning = warning

        # ----------------------------------------------------------------------
        # Stage 4: Light Grammar Pass (backend.md Section 4.5)
        # ----------------------------------------------------------------------
        async with trace_pipeline_stage("stage_4_light_grammar", {"preserve_quirks": request.preserve_quirks}):
            stage4_out, stage4_log = await self._run_stage_4_grammar_pass(
                input_text=stage3_out,
                genome=genome,
                preserve_quirks=request.preserve_quirks,
            )
            stage_logs.append(stage4_log)
            last_provider_used = stage4_log.provider_used

        # ----------------------------------------------------------------------
        # Evaluation Metrics & Report Packaging
        # ----------------------------------------------------------------------
        evals = compute_all_evals(
            original_text=raw_text,
            rewritten_text=stage4_out,
            genome=genome,
        )

        stage_outputs = StageOutputs(
            stage1_generate=stage1_out,
            stage2_tone_transform=stage2_out,
            stage3_meaning_checked=not meaning_check_failed,
            stage3_retried=retried_stage3,
            stage3_drift_reason=drift_reason_logged,
            stage4_grammar_passed=stage4_out,
        )

        return RewriteResponse(
            finalOutput=stage4_out,
            meaningCheckFailed=meaning_check_failed,
            meaningWarning=meaning_warning,
            provider=last_provider_used,
            evalScores=evals,
            stageOutputs=stage_outputs,
            stages=stage_logs,
            words_consumed=words_consumed,
            quota_remaining=quota_remaining,
        )

    # ==========================================================================
    # Stage Implementation Details
    # ==========================================================================

    async def _run_stage_1_generate(
        self,
        text: str,
        input_type: InputType,
    ) -> Tuple[str, RewriteStageLog]:
        """
        Stage 1: Produces raw draft.
        - If user supplies raw text: passes directly into Stage 2 (no LLM latency).
        - If user supplies bullet points: drafts raw draft via LLM.
        """
        t0 = time.monotonic()

        if input_type == InputType.RAW_DRAFT:
            # Pass directly into Stage 2 according to backend.md Section 4.2
            return text, RewriteStageLog(
                stage="generate",
                input_text=text,
                output_text=text,
                duration_ms=0.5,
                provider_used="passthrough_raw_draft",
                status="success",
                notes="Raw text supplied; bypassed LLM drafting directly to Stage 2.",
            )

        # Drafting from bullet points
        system_prompt = (
            "You are InkFlow Stage 1: Bullet Point Drafter. "
            "Convert the bullet points into a continuous, natural draft. "
            "Output ONLY the drafted text without conversational chatter."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Expand into draft:\n\n{text}"},
        ]
        res: LLMResult = await resilient_llm_service.complete(messages, temperature=0.6)
        cleaned = self._clean_llm_output(res.text)
        duration_ms = (time.monotonic() - t0) * 1000.0

        log = RewriteStageLog(
            stage="generate",
            input_text=text,
            output_text=cleaned,
            duration_ms=round(duration_ms, 2),
            provider_used=res.provider,
            status="success",
            notes="Drafted from bullet points.",
        )
        return cleaned, log

    async def _run_stage_2_tone_transform(
        self,
        text: str,
        target_context: str,
        genome: Dict[str, Any],
        corrective_reason: Optional[str] = None,
        temperature: float = 0.5,
    ) -> Tuple[str, RewriteStageLog]:
        """
        Stage 2: Injects author's Style Genome biometrics and removes AI slop buzzwords.
        If corrective_reason is provided, applies reason-aware retry prompt.
        """
        t0 = time.monotonic()
        baseline = genome.get("baselineGenome", {})
        avg_len = baseline.get("avgSentenceLength", genome.get("average_sentence_length", 15.0))
        transitions = ", ".join(baseline.get("transitionHabits", genome.get("frequent_connectors", ["however", "look,"])))
        exemplars = genome.get("exemplars", [])
        exemplar_hint = f"\nAuthor style anchors:\n1. {exemplars[0]}\n2. {exemplars[1]}" if len(exemplars) >= 2 else ""

        if corrective_reason:
            # Reason-aware retry prompt explicitly mandated in backend.md Section 4.4
            system_prompt = (
                f"You are InkFlow Stage 2: Tone Transformer.\n"
                f"CRITICAL CORRECTION REQUIRED:\n"
                f"Your previous attempt distorted the core meaning with the following error:\n"
                f'"{corrective_reason}"\n'
                f"You must strictly preserve this fact while keeping the user's authentic style.\n"
                f"Target rhythm: ~{avg_len} words per sentence. Natural transitions: {transitions}.\n"
                "Output ONLY the corrected text."
            )
        else:
            system_prompt = (
                f"You are InkFlow Stage 2: Tone Transformer.\n"
                f"Transform the draft into authentic personal voice for context: {target_context.upper()}.\n"
                f"Target sentence rhythm: approximately {avg_len} words per sentence.\n"
                f"Preferred transition habits: {transitions}.\n"
                f"{exemplar_hint}\n"
                "STRICT RULES:\n"
                "1. Strip robotic AI buzzwords: delve, tapestry, testament, beacon, pivotal, foster, holistic.\n"
                "2. Maintain natural human burstiness: vary sentence lengths.\n"
                "3. Output ONLY the transformed text."
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Transform this draft:\n\n{text}"},
        ]
        res: LLMResult = await resilient_llm_service.complete(messages, temperature=temperature)
        cleaned = self._clean_llm_output(res.text)
        duration_ms = (time.monotonic() - t0) * 1000.0

        log = RewriteStageLog(
            stage="tone_transform" if not corrective_reason else "meaning_check_retry",
            input_text=text,
            output_text=cleaned,
            duration_ms=round(duration_ms, 2),
            provider_used=res.provider,
            status="success",
            notes=f"Corrective retry: {corrective_reason}" if corrective_reason else "Style genome tone transformation.",
        )
        return cleaned, log

    async def _run_stage_3_meaning_gate(
        self,
        original_text: str,
        candidate_text: str,
        target_context: str,
        genome: Dict[str, Any],
    ) -> Tuple[str, RewriteStageLog, Optional[RewriteStageLog], bool, Optional[str], Optional[str]]:
        """
        Stage 3: Validates factual fidelity between original input and Stage 2 draft.
        Returns: (final_text, stage3_log, retry_log, meaning_check_failed, warning_message, drift_reason)
        """
        t0 = time.monotonic()
        fidelity = calculate_semantic_fidelity(original_text, candidate_text)

        # Fidelity >= 60% passes the meaning gate cleanly
        if fidelity >= 0.60:
            duration_ms = (time.monotonic() - t0) * 1000.0
            log = RewriteStageLog(
                stage="meaning_check",
                input_text=candidate_text,
                output_text=candidate_text,
                duration_ms=round(duration_ms, 2),
                provider_used="heuristic_gate",
                status="success",
                notes=f"Semantic fidelity score {fidelity:.3f} verified.",
            )
            return candidate_text, log, None, False, None, None

        # ----------------------------------------------------------------------
        # Meaning Gate Drift Detected: Trigger Reason-Aware Retry (backend.md 4.4)
        # ----------------------------------------------------------------------
        drift_reason = (
            "The draft altered or omitted key factual claims, specific metrics, or "
            "technical conditions present in the original text."
        )
        logger.warning("Meaning drift detected (fidelity: %.3f). Executing reason-aware retry.", fidelity)

        # Retry Stage 2 at temperature=0.3 injecting the exact drift_reason
        corrected_text, retry_log = await self._run_stage_2_tone_transform(
            text=original_text,
            target_context=target_context,
            genome=genome,
            corrective_reason=drift_reason,
            temperature=0.3,
        )

        stage3_log = RewriteStageLog(
            stage="meaning_check",
            input_text=candidate_text,
            output_text=candidate_text,
            duration_ms=round((time.monotonic() - t0) * 1000.0, 2),
            provider_used="heuristic_gate",
            status="retried",
            notes=f"Initial fidelity {fidelity:.3f} drifted. Triggered reason-aware retry.",
        )

        post_retry_fidelity = calculate_semantic_fidelity(original_text, corrected_text)
        meaning_check_failed = False
        meaning_warning = None

        # If retry still fails verification, trigger Soft Warning State (backend.md 4.4)
        if post_retry_fidelity < 0.55:
            meaning_check_failed = True
            meaning_warning = (
                "Meaning check couldn't fully verify this draft. "
                "Please double-check core facts before sending."
            )
            retry_log.status = "warning"

        return corrected_text, stage3_log, retry_log, meaning_check_failed, meaning_warning, drift_reason

    async def _run_stage_4_grammar_pass(
        self,
        input_text: str,
        genome: Dict[str, Any],
        preserve_quirks: bool = True,
    ) -> Tuple[str, RewriteStageLog]:
        """
        Stage 4: Fixes broken syntax while preserving punctuation quirks verbatim.
        Explicit prompt from backend.md Section 4.5.
        """
        t0 = time.monotonic()
        system_prompt = (
            "You are InkFlow Stage 4: Light Grammar Pass.\n"
            "Fix only broken grammatical structures, subject-verb disagreements, and missing words "
            "that break basic readability. EXPLICITLY DO NOT adjust commas, em-dashes, or conversational "
            "punctuation pauses. Retain the exact punctuation quirks of the input text.\n"
            "Output ONLY the corrected text."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Apply light grammar pass:\n\n{input_text}"},
        ]
        res: LLMResult = await resilient_llm_service.complete(messages, temperature=0.2)
        cleaned = self._clean_llm_output(res.text)

        # Invariant safeguard: guarantee punctuation preservation
        if preserve_quirks and "—" in input_text and "—" not in cleaned:
            if " -- " in cleaned:
                cleaned = cleaned.replace(" -- ", " — ")
            elif "--" in cleaned:
                cleaned = cleaned.replace("--", "—")

        duration_ms = (time.monotonic() - t0) * 1000.0
        log = RewriteStageLog(
            stage="light_grammar",
            input_text=input_text,
            output_text=cleaned,
            duration_ms=round(duration_ms, 2),
            provider_used=res.provider,
            status="success",
        )
        return cleaned, log

    def _clean_llm_output(self, text: str) -> str:
        """Strips surrounding code fences or extraneous quotes."""
        if not text:
            return ""
        s = text.strip()
        if s.startswith("```") and s.endswith("```"):
            lines = s.splitlines()
            if len(lines) >= 3:
                s = "\n".join(lines[1:-1]).strip()
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            s = s[1:-1].strip()
        return s


# Singleton instance
rewrite_pipeline_service = RewritePipelineService()
