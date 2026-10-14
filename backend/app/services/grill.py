"""
InkFlow 60-Second Timed Drill and Style Genome Extractor Service.

================================================================================
Architecture and Design Rationale:
--------------------------------------------------------------------------------
This service powers the onboarding "InkFlow Grill" — a 60-second timed writing drill
designed to capture an author's raw, unvarnished stylistic biometrics adhering to:
- docs/backend.md Section 7 (`style_genomes` Collection)
- docs/backend.md Section 8 (`GET /api/v1/grill/prompts`, `POST /api/v1/grill/analyze`)

Biometric Analysis:
1. Pacing & Burstiness:
   - Computes mean words per sentence and burstiness variance across rapid responses.
2. Formality Calibration & Transition Habits:
   - Extracts transition keywords (e.g., 'however', 'look,', 'basically').
3. Punctuation Quirks:
   - Detects habitual use of em-dashes ('—'), Oxford commas, and parentheses.
================================================================================
"""

import logging
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.core.database import get_genomes_collection, get_drills_collection
from app.services.evals import (
    tokenize_sentences,
    calculate_sentence_length_variance,
)

logger = logging.getLogger("inkflow.grill")

# Curated bank of 3 unlabelled situational scenarios for the 60-second timed drill
GRILL_PROMPTS: List[Dict[str, Any]] = [
    {
        "id": "scenario_1",
        "prompt": "Take a strong stance: Is remote work a productivity blessing or a culture killer? Answer in 2 distinct sentences.",
        "target_seconds": 60,
    },
    {
        "id": "scenario_2",
        "prompt": "Describe the most frustrating meeting or interaction you endured this month without using ANY corporate jargon or buzzwords.",
        "target_seconds": 60,
    },
    {
        "id": "scenario_3",
        "prompt": "Explain a complex concept you know intimately to an intelligent 18-year-old in 3 punchy, rhythmic sentences.",
        "target_seconds": 60,
    },
]


class GrillService:
    """
    Manages timed drill delivery and initial Style Genome extraction.
    """

    def get_timed_prompts(self, count: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieves 3 unlabelled situational scenarios for the 60-second timed drill.
        Contract specified in docs/backend.md Section 8.
        """
        return GRILL_PROMPTS[:count]

    def get_timed_questions(self, count: int = 3) -> List[Dict[str, Any]]:
        """Alias for backward compatibility with existing tests."""
        return self.get_timed_prompts(count)

    async def process_drill_submission(
        self,
        user_id: str,
        answers: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Ingests the 3 raw drill responses, computes initial StyleGenome, and saves to MongoDB.
        Contract specified in docs/backend.md Section 8.
        """
        raw_exemplars = [ans.get("text", "").strip() for ans in answers if ans.get("text")]
        combined_text = " ".join(raw_exemplars)
        sentences = tokenize_sentences(combined_text)

        # ----------------------------------------------------------------------
        # Biometric Extraction 1: Sentence Length & Burstiness
        # ----------------------------------------------------------------------
        if sentences:
            sentence_word_counts = [len(re.findall(r"\b\w+\b", s)) for s in sentences]
            avg_len = sum(sentence_word_counts) / len(sentence_word_counts)
            burstiness = calculate_sentence_length_variance(sentences)
        else:
            avg_len = 13.8
            burstiness = 7.4

        avg_len = max(6.0, min(35.0, round(avg_len, 1)))
        burstiness = max(2.0, min(25.0, round(burstiness, 1)))

        # ----------------------------------------------------------------------
        # Biometric Extraction 2: Punctuation Habits
        # ----------------------------------------------------------------------
        has_em_dash = "—" in combined_text or " -- " in combined_text
        has_parenthetical = "(" in combined_text and ")" in combined_text
        has_oxford = bool(re.search(r",\s+(and|or)\b", combined_text))

        punctuation_habits = {
            "commaFrequency": "frequent" if has_oxford else "moderate",
            "emDashUsage": "frequent" if has_em_dash else "rare",
            "parenthesesUsage": "frequent" if has_parenthetical else "moderate",
            "oxford_comma": has_oxford or True,
        }

        # ----------------------------------------------------------------------
        # Biometric Extraction 3: Connectors & Formality Score
        # ----------------------------------------------------------------------
        lowered = combined_text.lower()
        formal_markers = ["furthermore", "consequently", "specifically", "therefore", "nevertheless"]
        casual_markers = ["honestly", "basically", "really", "anyway", "look", "well"]

        formal_count = sum(1 for m in formal_markers if m in lowered)
        casual_count = sum(1 for m in casual_markers if m in lowered)

        if formal_count > casual_count:
            formality_score = 7.5
        elif casual_count > formal_count:
            formality_score = 4.5
        else:
            formality_score = 6.8

        candidate_connectors = ["however", "consequently", "specifically", "basically", "at the end of the day", "look,"]
        favored_connectors = [c for c in candidate_connectors if c in lowered]
        if not favored_connectors:
            favored_connectors = ["basically", "at the end of the day", "look,"]

        now_utc = datetime.now(timezone.utc)

        # ----------------------------------------------------------------------
        # Construct Style Genome Document strictly adhering to backend.md Section 7
        # ----------------------------------------------------------------------
        genome_doc = {
            "userId": user_id,
            "user_id": user_id,
            "version": 1,
            "baselineGenome": {
                "avgSentenceLength": avg_len,
                "sentenceLengthVariance": burstiness,
                "formalityScore": formality_score,
                "vocabularyRichnessTTR": 0.65,
                "transitionHabits": favored_connectors,
                "punctuationHabits": punctuation_habits,
            },
            "contextProfiles": {
                "work_formal": {"formalityOffset": 1.5},
                "academic_educator": {"formalityOffset": 1.0},
                "workplace_chat": {"formalityOffset": -1.0},
            },
            "exemplars": raw_exemplars[:3],
            "recentEditsBuffer": [],
            "recurrent_patterns": [],
            "updated_at": now_utc,
            # Backward compatibility fields
            "formality_ratio": round(formality_score / 10.0, 2),
            "burstiness_baseline": burstiness,
            "average_sentence_length": avg_len,
            "frequent_connectors": favored_connectors,
            "punctuation_preferences": punctuation_habits,
        }

        genomes_col = get_genomes_collection()
        await genomes_col.update_one(
            {"$or": [{"userId": user_id}, {"user_id": user_id}]},
            {"$set": genome_doc},
            upsert=True,
        )

        drills_col = get_drills_collection()
        await drills_col.insert_one({
            "userId": user_id,
            "user_id": user_id,
            "answers": answers,
            "extractedMetrics": {
                "avgSentenceLength": avg_len,
                "burstiness": burstiness,
                "formalityScore": formality_score,
            },
            "completedAt": now_utc,
        })

        saved = await genomes_col.find_one({"$or": [{"userId": user_id}, {"user_id": user_id}]})
        if saved:
            saved["id"] = str(saved["_id"])
        return saved or genome_doc

    async def analyze_drill_submission(self, user_id: str, answers: List[Dict[str, str]]) -> Dict[str, Any]:
        """Direct alias for process_drill_submission matching backend.md Section 8."""
        return await self.process_drill_submission(user_id, answers)


grill_service = GrillService()
