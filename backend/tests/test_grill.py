"""
InkFlow Automated Tests: Timed Drill and Genome Extraction Suite.

================================================================================
Test Rationale and Verification Coverage:
--------------------------------------------------------------------------------
This test module verifies the onboarding "InkFlow Grill" service:
1. `get_timed_questions`:
   - Verifies that curated rapid-fire writing prompts are returned with target duration tags.
2. `process_drill_submission`:
   - Verifies that biometric metrics (burstiness, mean sentence length, punctuation preferences,
     and formality) are extracted accurately from submitted text.
   - Verifies that the resulting Style Genome is persisted to MongoDB and returned to the caller.
================================================================================
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from bson import ObjectId

from app.services.grill import GrillService


def test_get_timed_questions_returns_curated_prompts():
    """
    Verifies that get_timed_questions returns the requested count of prompts
    with necessary fields.
    """
    service = GrillService()
    questions = service.get_timed_questions(count=3)

    assert len(questions) == 3
    for q in questions:
        assert "id" in q
        assert "prompt" in q
        assert "target_seconds" in q
        assert q["target_seconds"] == 60


@pytest.mark.asyncio
async def test_process_drill_submission_extracts_and_persists_genome():
    """
    Verifies that processing user drill answers calculates biometric baselines
    and stores the calibrated Style Genome.
    """
    service = GrillService()
    user_id = str(ObjectId())

    # Realistic rapid-fire answers displaying distinct cadence, em-dashes, and Oxford commas
    answers = [
        {
            "question_id": "q1",
            "text": "Remote work is an undisputed productivity blessing for autonomous thinkers. It cuts pointless commuting and protects deep concentration.",
        },
        {
            "question_id": "q2",
            "text": "We endured two hours debating font weights across staging, test, and production environments; the conclusion was obvious — stick to default sans-serif.",
        },
        {
            "question_id": "q3",
            "text": "Quantum computers manipulate superposition states. They process massive solution spaces simultaneously. Classical silicon simply cannot compete.",
        },
    ]

    mock_genomes_col = MagicMock()
    mock_genomes_col.update_one = AsyncMock()
    mock_genomes_col.find_one = AsyncMock(return_value={
        "_id": ObjectId(),
        "user_id": user_id,
        "formality_ratio": 0.60,
        "burstiness_baseline": 8.2,
        "average_sentence_length": 13.5,
        "passive_voice_tolerance": 0.12,
        "vocabulary_tier": "professional",
        "frequent_connectors": ["specifically", "however"],
        "punctuation_preferences": {
            "oxford_comma": True,
            "em_dash_frequency": 0.4,
            "semicolon_preference": 0.3,
            "parenthetical_asides": True,
        },
        "custom_rules": [],
        "recurrent_patterns": [],
    })

    mock_drills_col = MagicMock()
    mock_drills_col.insert_one = AsyncMock()

    with patch("app.services.grill.get_genomes_collection", return_value=mock_genomes_col), \
         patch("app.services.grill.get_drills_collection", return_value=mock_drills_col):

        genome = await service.process_drill_submission(user_id=user_id, answers=answers)

        assert genome["user_id"] == user_id
        assert "burstiness_baseline" in genome
        assert "average_sentence_length" in genome
        assert "punctuation_preferences" in genome

        # Verify database interactions
        mock_genomes_col.update_one.assert_awaited_once()
        mock_drills_col.insert_one.assert_awaited_once()
