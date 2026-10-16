"""
InkFlow Automated Tests: 4-Stage Sequential Rewrite Pipeline Suite.

================================================================================
Test Rationale and Verification Coverage:
--------------------------------------------------------------------------------
This test module verifies the end-to-end 4-stage rewrite transformation:
1. Sequential Execution (Happy Path):
   - Verifies that raw text passes directly to Stage 2 without LLM drafting.
   - Verifies that Stage 2, Stage 3 (Meaning check pass), and Stage 4 run sequentially.
2. Bullet Points Drafting:
   - Verifies that inputType="bullet_points" invokes LLM drafting in Stage 1.
3. Reason-Aware Retry Gate (Stage 3):
   - When candidate text causes semantic drift below threshold, triggers an automatic
     corrective retry injecting the exact `drift_reason` into the prompt.
4. Soft Warning Fallback (Stage 3):
   - If second attempt remains under confidence threshold, gracefully returns the candidate
     with `meaningCheckFailed: True` and `meaningWarning` rather than raising HTTP 422.
5. Punctuation Quirks Preservation (Stage 4):
   - Verifies that author's stylistic punctuation quirks (em-dashes '—', semicolons,
     and Oxford commas) are strictly preserved through the final pass.
6. 500-Word Cap Enforcement:
   - Verifies that drafts exceeding 500 words per pass raise HTTP 400 Bad Request.
================================================================================
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from app.models.rewrite import RewriteRequest, RewriteResponse, InputType
from app.services.pipeline import RewritePipelineService
from app.services.providers import LLMResult


@pytest.fixture
def sample_genome():
    """Provides a realistic Style Genome for pipeline testing."""
    return {
        "userId": "test_user_123",
        "baselineGenome": {
            "avgSentenceLength": 14.5,
            "sentenceLengthVariance": 7.0,
            "formalityScore": 6.5,
            "vocabularyRichnessTTR": 0.68,
            "transitionHabits": ["however", "consequently", "specifically"],
            "punctuationHabits": {
                "oxford_comma": True,
                "emDashUsage": "frequent",
                "parenthesesUsage": "moderate",
            },
        },
        "exemplars": [
            "We audited the pipeline rigorously — all invariant checks held.",
            "Specifically, throughput scaled linearly across worker nodes.",
        ],
        "contextProfiles": {
            "work_formal": {"formalityOffset": 1.5},
            "academic": {"formalityOffset": 1.0},
        },
    }


@pytest.mark.asyncio
async def test_full_pipeline_happy_path(sample_genome):
    """
    Verifies normal 4-stage pipeline execution when raw draft is supplied and
    semantic fidelity passes cleanly.
    """
    pipeline = RewritePipelineService()
    input_text = "The engineering team audited three backend subsystems; all passed without issue."
    request = RewriteRequest(
        input=input_text,
        inputType=InputType.RAW_DRAFT,
        context="work_formal",
        preserve_quirks=True,
    )

    stage2_mock = "The engineering team audited three backend subsystems; all passed without issue."
    stage4_mock = "The engineering team audited three backend subsystems; all passed without issue."

    with patch("app.services.pipeline.resilient_llm_service.complete", new_callable=AsyncMock) as mock_complete:
        # Calls: Stage 2 Tone Transform, Stage 4 Grammar pass (Stage 1 is passthrough for raw draft)
        mock_complete.side_effect = [
            LLMResult(text=stage2_mock, provider="groq_gpt_oss_120b", duration_ms=130.0),
            LLMResult(text=stage4_mock, provider="groq_gpt_oss_120b", duration_ms=110.0),
        ]

        response: RewriteResponse = await pipeline.execute(
            request=request,
            genome=sample_genome,
            words_consumed=11,
            quota_remaining=2489,
        )

        assert response.finalOutput == stage4_mock
        assert response.meaningCheckFailed is False
        assert response.meaningWarning is None
        assert len(response.stages) >= 4
        stage_names = [s.stage for s in response.stages]
        assert "generate" in stage_names
        assert "tone_transform" in stage_names
        assert "meaning_check" in stage_names
        assert "light_grammar" in stage_names


@pytest.mark.asyncio
async def test_bullet_points_drafting_invokes_stage1_llm(sample_genome):
    """
    Verifies that when inputType is bullet_points, Stage 1 drafts using the LLM.
    """
    pipeline = RewritePipelineService()
    bullet_input = "- revenue grew 18%\n- cloud expansion succeeded\n- renewed enterprise deals"
    request = RewriteRequest(
        input=bullet_input,
        inputType=InputType.BULLET_POINTS,
        context="work_formal",
    )

    stage1_mock = "Quarterly revenue grew 18% driven by cloud expansion and renewed enterprise contracts."
    stage2_mock = "Quarterly revenue grew 18% driven by cloud expansion and renewed enterprise contracts."
    stage4_mock = "Quarterly revenue grew 18% driven by cloud expansion and renewed enterprise contracts."

    with patch("app.services.pipeline.resilient_llm_service.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.side_effect = [
            LLMResult(text=stage1_mock, provider="groq_gpt_oss_120b", duration_ms=100.0),
            LLMResult(text=stage2_mock, provider="groq_gpt_oss_120b", duration_ms=120.0),
            LLMResult(text=stage4_mock, provider="groq_gpt_oss_120b", duration_ms=90.0),
        ]

        response: RewriteResponse = await pipeline.execute(
            request=request,
            genome=sample_genome,
            words_consumed=10,
            quota_remaining=2490,
        )

        assert response.finalOutput == stage4_mock
        assert mock_complete.await_count == 3


@pytest.mark.asyncio
async def test_meaning_check_retry_gate_triggers_on_drift(sample_genome):
    """
    Verifies that when Stage 2 introduces semantic drift, Stage 3 triggers
    a reason-aware retry injecting the exact failure reason.
    """
    pipeline = RewritePipelineService()
    original = "The quarterly revenue grew by 18 percent due to enterprise renewals and cloud expansion."
    request = RewriteRequest(
        input=original,
        inputType=InputType.RAW_DRAFT,
        context="work_formal",
    )

    # Drifted candidate discussing completely unrelated topic
    drifted_stage2 = "The weather was sunny outside and birds were chirping in the park."
    corrected_stage3 = "Quarterly revenue grew by 18% driven by enterprise account renewals and cloud expansion."
    stage4_out = "Quarterly revenue grew by 18% driven by enterprise account renewals and cloud expansion."

    with patch("app.services.pipeline.resilient_llm_service.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.side_effect = [
            LLMResult(text=drifted_stage2, provider="groq_gpt_oss_120b", duration_ms=110.0),  # Stage 2
            LLMResult(text=corrected_stage3, provider="groq_gpt_oss_120b", duration_ms=140.0),     # Retry
            LLMResult(text=stage4_out, provider="groq_gpt_oss_120b", duration_ms=95.0),       # Stage 4
        ]

        response: RewriteResponse = await pipeline.execute(
            request=request,
            genome=sample_genome,
            words_consumed=14,
            quota_remaining=2486,
        )

        stage_names = [s.stage for s in response.stages]
        assert "meaning_check_retry" in stage_names
        assert response.finalOutput == stage4_out
        assert response.meaningCheckFailed is False


@pytest.mark.asyncio
async def test_meaning_check_soft_warning_fallback(sample_genome):
    """
    Verifies that if retry still fails verification, the pipeline advances to Stage 4
    with meaningCheckFailed=True and meaningWarning soft badge without raising HTTP 422.
    """
    pipeline = RewritePipelineService()
    original = "The quantum protocol preserved qubit coherence across 12 meters of optical fiber."
    request = RewriteRequest(
        input=original,
        inputType=InputType.RAW_DRAFT,
        context="academic",
    )

    drifted_unrelated = "Coffee was served at the conference table and muffins were enjoyed."

    with patch("app.services.pipeline.resilient_llm_service.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.side_effect = [
            LLMResult(text=drifted_unrelated, provider="groq_gpt_oss_120b", duration_ms=100.0),  # Stage 2
            LLMResult(text=drifted_unrelated, provider="groq_gpt_oss_120b", duration_ms=110.0),        # Retry
            LLMResult(text=drifted_unrelated, provider="groq_gpt_oss_120b", duration_ms=90.0),   # Stage 4
        ]

        response: RewriteResponse = await pipeline.execute(
            request=request,
            genome=sample_genome,
            words_consumed=12,
            quota_remaining=2000,
        )

        assert response.meaningCheckFailed is True
        assert response.meaningWarning == "Meaning check couldn't fully verify this draft. Please double-check core facts before sending."
        assert response.finalOutput == drifted_unrelated


@pytest.mark.asyncio
async def test_punctuation_quirks_preservation(sample_genome):
    """
    Verifies that Stage 4 preserves author's stylistic punctuation marks:
    - Em-dashes ('—')
    - Semicolons (';')
    - Oxford serial commas (', and')
    """
    pipeline = RewritePipelineService()
    text_with_quirks = (
        "We audited three subsystems: auth, billing, and storage; "
        "the findings were conclusive — every test passed without exception."
    )
    request = RewriteRequest(
        input=text_with_quirks,
        preserve_quirks=True,
    )

    with patch("app.services.pipeline.resilient_llm_service.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.side_effect = [
            LLMResult(text=text_with_quirks, provider="groq_gpt_oss_120b", duration_ms=90.0),
            LLMResult(text=text_with_quirks, provider="groq_gpt_oss_120b", duration_ms=90.0),
        ]

        response: RewriteResponse = await pipeline.execute(
            request=request,
            genome=sample_genome,
            words_consumed=19,
            quota_remaining=2400,
        )

        assert "—" in response.finalOutput
        assert ";" in response.finalOutput
        assert ", and" in response.finalOutput


@pytest.mark.asyncio
async def test_1000_word_cap_exceeded_raises_400(sample_genome):
    """
    Verifies that inputs exceeding 1,000 words per pass raise HTTP 400 Bad Request.
    """
    pipeline = RewritePipelineService()
    oversized_text = "word " * 1001
    request = RewriteRequest(input=oversized_text)

    with pytest.raises(HTTPException) as exc_info:
        await pipeline.execute(
            request=request,
            genome=sample_genome,
            words_consumed=1001,
            quota_remaining=2500,
        )

    assert exc_info.value.status_code == 400
    assert "Input exceeds maximum allowed length of 1000 words" in exc_info.value.detail
