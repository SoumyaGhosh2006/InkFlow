"""
InkFlow Automated Tests: Adaptive Learning and 3-Session Recurrence Filter Suite.

================================================================================
Test Rationale and Verification Coverage:
--------------------------------------------------------------------------------
This test module verifies the noise-resistant adaptive learning engine:
1. One-off Noise Immunity:
   - Verifies that an edit in a single session is stored in pending_patterns
     with session_count=1 and is NOT promoted to the permanent Style Genome.
2. Intra-Session Deduplication:
   - Verifies that making the same edit multiple times within the SAME session
     does not increment session count.
3. Cross-Session Promotion Gate:
   - Verifies that only when the same pattern recurs across THREE (>=3) distinct
     sessions is it promoted to `recurrent_patterns` in the user's Style Genome.
4. Unmodified Acceptance:
   - Verifies that accepting text without edits produces zero detected patterns.
================================================================================
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from bson import ObjectId

from app.services.adaptive import AdaptiveLearningService


@pytest.mark.asyncio
async def test_adaptive_unmodified_text_produces_no_patterns():
    """
    Verifies that when the user accepts text verbatim without manual modifications,
    the adaptive learner takes no action.
    """
    service = AdaptiveLearningService()
    text = "Everything was accurate and acceptable without revisions."

    result = await service.record_session_diff(
        user_id="user_1",
        session_id="session_101",
        generated_text=text,
        user_edited_text=text,
    )
    assert result == []


@pytest.mark.asyncio
async def test_single_session_edit_remains_pending():
    """
    Verifies that an edit observed in only one session remains pending
    and is NOT promoted to the permanent Style Genome.
    """
    service = AdaptiveLearningService()
    user_id = "user_2"
    session_id = "session_A"

    generated = "The result was clear. Everyone agreed."
    # User adds an em-dash in their edit
    user_edited = "The result was clear — everyone agreed."

    mock_pending_col = MagicMock()
    mock_pending_col.find_one = AsyncMock(return_value=None)  # First time seen
    mock_pending_col.insert_one = AsyncMock()

    mock_db = {"pending_patterns": mock_pending_col}

    with patch("app.services.adaptive.get_db", return_value=mock_db), \
         patch.object(service, "_promote_to_genome", new_callable=AsyncMock) as mock_promote:

        promoted = await service.record_session_diff(
            user_id=user_id,
            session_id=session_id,
            generated_text=generated,
            user_edited_text=user_edited,
        )

        # Should not be promoted yet
        assert promoted == []
        mock_pending_col.insert_one.assert_awaited_once()
        mock_promote.assert_not_called()


@pytest.mark.asyncio
async def test_same_session_repeated_edits_do_not_increment_counter():
    """
    Verifies that repeating an edit within the SAME session does not count as multiple sessions.
    """
    service = AdaptiveLearningService()
    user_id = "user_3"
    session_id = "session_A"

    generated = "The result was clear. Everyone agreed."
    user_edited = "The result was clear — everyone agreed."

    existing_record = {
        "_id": ObjectId(),
        "user_id": user_id,
        "rule_key": "prefers_em_dashes",
        "description": "User prefers em-dashes",
        "sessions": [session_id],  # Already observed in session_A
        "session_count": 1,
        "is_promoted": False,
    }

    mock_pending_col = MagicMock()
    mock_pending_col.find_one = AsyncMock(return_value=existing_record)
    mock_pending_col.update_one = AsyncMock()

    mock_db = {"pending_patterns": mock_pending_col}

    with patch("app.services.adaptive.get_db", return_value=mock_db), \
         patch.object(service, "_promote_to_genome", new_callable=AsyncMock) as mock_promote:

        promoted = await service.record_session_diff(
            user_id=user_id,
            session_id=session_id,
            generated_text=generated,
            user_edited_text=user_edited,
        )

        assert promoted == []
        # No updates because session_A is already in the sessions list
        mock_pending_col.update_one.assert_not_called()
        mock_promote.assert_not_called()


@pytest.mark.asyncio
async def test_three_distinct_sessions_triggers_genome_promotion():
    """
    Verifies that when a pattern is observed across 3 separate sessions (session_A, session_B, session_C),
    it satisfies the >=3 recurrence gate and is promoted to the permanent Style Genome.
    """
    service = AdaptiveLearningService()
    user_id = "user_4"
    current_session = "session_C"

    generated = "The result was clear. Everyone agreed."
    user_edited = "The result was clear — everyone agreed."

    existing_record = {
        "_id": ObjectId(),
        "user_id": user_id,
        "rule_key": "prefers_em_dashes",
        "description": "User prefers em-dashes",
        "sessions": ["session_A", "session_B"],  # Already seen in 2 distinct sessions
        "session_count": 2,
        "is_promoted": False,
    }

    mock_pending_col = MagicMock()
    mock_pending_col.find_one = AsyncMock(return_value=existing_record)
    mock_pending_col.update_one = AsyncMock()

    mock_db = {"pending_patterns": mock_pending_col}

    with patch("app.services.adaptive.get_db", return_value=mock_db), \
         patch.object(service, "_promote_to_genome", new_callable=AsyncMock) as mock_promote:

        promoted = await service.record_session_diff(
            user_id=user_id,
            session_id=current_session,
            generated_text=generated,
            user_edited_text=user_edited,
        )

        # Must be promoted!
        assert len(promoted) == 1
        assert promoted[0]["rule_key"] == "prefers_em_dashes"
        assert promoted[0]["promoted"] is True
        assert promoted[0]["sessions"] == 3
        mock_promote.assert_awaited_once()
        mock_pending_col.update_one.assert_awaited_once()


@pytest.mark.asyncio
async def test_genome_integrity_protection_skips_failed_meaning_check():
    """
    Verifies that when a rewrite had meaningCheckFailed=True,
    the adaptive learning engine explicitly skips the genome training loop.
    Directly satisfies the Genome Integrity Protection rule in backend.md Section 8.
    """
    service = AdaptiveLearningService()
    user_id = "user_integrity_test"
    rewrite_id = str(ObjectId())

    mock_rewrite = {
        "_id": ObjectId(rewrite_id),
        "finalOutput": "Generated text that had semantic shift",
        "meaningCheckFailed": True,
        "meaningWarning": "Meaning check couldn't fully verify this draft.",
    }

    mock_rewrites_col = MagicMock()
    mock_rewrites_col.find_one = AsyncMock(return_value=mock_rewrite)

    with patch("app.services.adaptive.get_rewrites_collection", return_value=mock_rewrites_col), \
         patch.object(service, "record_session_diff", new_callable=AsyncMock) as mock_record_diff:

        result = await service.process_accepted_rewrite(
            user_id=user_id,
            rewrite_id=rewrite_id,
            final_user_text="User edited text with adjustments",
        )

        assert result["status"] == "skipped"
        assert "Genome Integrity Protection" in result["reason"]
        mock_record_diff.assert_not_called()

