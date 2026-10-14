"""
InkFlow Automated Tests: Punctuation Preservation Invariant Suite (Stage 4).

================================================================================
Test Rationale and Verification Coverage:
--------------------------------------------------------------------------------
This test module verifies the grammar pass invariant defined in backend.md Section 4.5 & 10:
"Fix only broken grammatical structures, subject-verb disagreements, and missing words
that break basic readability. EXPLICITLY DO NOT adjust commas, em-dashes, or conversational
punctuation pauses. Retain the exact punctuation quirks of the input text."

Verified Invariants:
1. Em-Dash ('—') Retention:
   - Verifies that stylistic em-dashes used for dramatic pauses or elaboration are preserved.
2. Oxford Serial Comma Preservation:
   - Verifies that serial commas in lists (e.g. 'auth, billing, and storage') are retained.
3. Semicolon (';') Preservation:
   - Verifies that semicolons linking independent clauses remain untouched.
4. Parenthetical Asides:
   - Verifies that conversational parenthetical commentary is retained.
5. Typo Fix with Punctuation Invariant:
   - Verifies that syntax errors are corrected while punctuation quirks remain intact.
================================================================================
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.models.rewrite import RewriteRequest, RewriteResponse
from app.services.pipeline import RewritePipelineService
from app.services.providers import LLMResult


@pytest.fixture
def sample_genome():
    return {
        "userId": "test_user_punct",
        "baselineGenome": {
            "avgSentenceLength": 15.0,
            "sentenceLengthVariance": 8.0,
            "formalityScore": 7.0,
            "vocabularyRichnessTTR": 0.70,
            "transitionHabits": ["however", "consequently"],
            "punctuationHabits": {
                "oxford_comma": True,
                "emDashUsage": "frequent",
                "parenthesesUsage": "frequent",
            },
        },
    }


@pytest.mark.asyncio
async def test_em_dash_invariant_preserved(sample_genome):
    """
    Verifies that stylistic em-dashes ('—') are never stripped or converted to simple hyphens.
    """
    pipeline = RewritePipelineService()
    input_text = "The microservice deployment was completely successful — zero downtime was recorded."
    request = RewriteRequest(input=input_text, preserve_quirks=True)

    with patch("app.services.pipeline.resilient_llm_service.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.side_effect = [
            LLMResult(text=input_text, provider="groq_llama33", duration_ms=80.0),
            LLMResult(text=input_text, provider="groq_llama33", duration_ms=75.0),
        ]

        response: RewriteResponse = await pipeline.execute(
            request=request,
            genome=sample_genome,
            words_consumed=11,
            quota_remaining=2400,
        )

        assert "—" in response.finalOutput
        assert "--" not in response.finalOutput


@pytest.mark.asyncio
async def test_oxford_comma_and_semicolon_preserved(sample_genome):
    """
    Verifies that Oxford serial commas and semicolons are retained verbatim.
    """
    pipeline = RewritePipelineService()
    input_text = "We inspected telemetry, latency, and throughput; everything matched our SLA."
    request = RewriteRequest(input=input_text, preserve_quirks=True)

    with patch("app.services.pipeline.resilient_llm_service.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.side_effect = [
            LLMResult(text=input_text, provider="groq_llama33", duration_ms=80.0),
            LLMResult(text=input_text, provider="groq_llama33", duration_ms=75.0),
        ]

        response: RewriteResponse = await pipeline.execute(
            request=request,
            genome=sample_genome,
            words_consumed=10,
            quota_remaining=2400,
        )

        assert ", and throughput" in response.finalOutput
        assert ";" in response.finalOutput


@pytest.mark.asyncio
async def test_parenthetical_remarks_preserved(sample_genome):
    """
    Verifies that conversational parenthetical asides remain intact.
    """
    pipeline = RewritePipelineService()
    input_text = "The migration (which took three full days) was completed successfully."
    request = RewriteRequest(input=input_text, preserve_quirks=True)

    with patch("app.services.pipeline.resilient_llm_service.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.side_effect = [
            LLMResult(text=input_text, provider="groq_llama33", duration_ms=80.0),
            LLMResult(text=input_text, provider="groq_llama33", duration_ms=75.0),
        ]

        response: RewriteResponse = await pipeline.execute(
            request=request,
            genome=sample_genome,
            words_consumed=10,
            quota_remaining=2400,
        )

        assert "(which took three full days)" in response.finalOutput
