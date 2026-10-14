"""
InkFlow Style Genome Domain Model and Schemas.

================================================================================
Architecture and Design Rationale:
--------------------------------------------------------------------------------
The Style Genome is the biometric profile of an author's writing twin.
Adheres strictly to docs/backend.md Section 7:

Style Genome Schema (`style_genomes` Collection):
- userId: String index linking genome to user.
- version: Integer schema version (defaults to 1).
- baselineGenome:
    - avgSentenceLength: Mean words per sentence.
    - sentenceLengthVariance: Burstiness variance.
    - formalityScore: Scaled formality score (0.0 to 10.0 or 0.0 to 1.0).
    - vocabularyRichnessTTR: Type-Token Ratio from user's accepted text.
    - transitionHabits: List of favorite transition words and starters.
    - punctuationHabits: Frequency of commas, em-dashes, and parentheses.
- contextProfiles: Offsets for 'work_formal', 'academic_educator', and 'workplace_chat'.
- exemplars: List of raw verbatim exemplar strings from the onboarding drill.
- recentEditsBuffer: Rolling window of accepted edits with rewriteId, timestamp, and editType.
================================================================================
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class PunctuationHabits(BaseModel):
    """
    Granular punctuation habits preserved throughout all rewrite stages.
    """
    commaFrequency: str = Field(default="moderate", description="Frequency: rare, moderate, frequent.")
    emDashUsage: str = Field(default="rare", description="Usage of em-dashes: rare, moderate, frequent.")
    parenthesesUsage: str = Field(default="frequent", description="Usage of parentheses: rare, moderate, frequent.")
    oxford_comma: bool = Field(default=True, description="Preservation of Oxford comma.")


class BaselineGenome(BaseModel):
    """
    Calibrated biometric writing baseline.
    """
    avgSentenceLength: float = Field(default=13.8, ge=3.0, le=60.0, description="Mean words per sentence.")
    sentenceLengthVariance: float = Field(default=7.4, ge=0.0, description="Burstiness variance.")
    formalityScore: float = Field(default=6.8, ge=0.0, le=10.0, description="Formality score on 0-10 scale.")
    vocabularyRichnessTTR: float = Field(default=0.65, ge=0.0, le=1.0, description="Type-Token Ratio.")
    transitionHabits: List[str] = Field(
        default_factory=lambda: ["basically", "at the end of the day", "look,"],
        description="List of favored transition starters.",
    )
    punctuationHabits: PunctuationHabits = Field(default_factory=PunctuationHabits)


class ContextProfile(BaseModel):
    """
    Context-specific adjustments to the baseline genome.
    """
    formalityOffset: float = Field(default=0.0, description="Offset applied to formalityScore.")


class RecentEdit(BaseModel):
    """
    Individual entry in the recent edits buffer for noise-resistant adaptive learning.
    """
    rewriteId: str = Field(..., description="Stringified ObjectId of the rewrite.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    editType: str = Field(..., description="Type of edit: e.g. shortened_sentences, added_em_dash.")
    detail: str = Field(..., description="Details of stylistic shift.")


class RecurrentPattern(BaseModel):
    """
    Persistent habit verified through the >=3 session adaptive filter.
    """
    rule_key: str = Field(..., description="Unique slug identifying the pattern.")
    description: str = Field(..., description="Human-readable rule instruction.")
    session_count: int = Field(..., ge=3, description="Distinct sessions in which habit recurred.")
    first_detected: datetime = Field(..., description="UTC timestamp of first observation.")
    promoted_at: datetime = Field(..., description="UTC timestamp when threshold was reached.")


class StyleGenomeResponse(BaseModel):
    """
    Public representation of author's Style Genome profile.
    """
    id: Optional[str] = Field(None, description="Stringified MongoDB ObjectId.")
    userId: str = Field(..., description="Associated user ID.")
    version: int = Field(default=1, description="Schema version.")
    baselineGenome: BaselineGenome = Field(default_factory=BaselineGenome)
    contextProfiles: Dict[str, ContextProfile] = Field(
        default_factory=lambda: {
            "work_formal": ContextProfile(formalityOffset=1.5),
            "academic_educator": ContextProfile(formalityOffset=1.0),
            "workplace_chat": ContextProfile(formalityOffset=-1.0),
        }
    )
    exemplars: List[str] = Field(default_factory=list, description="Raw exemplars from drill.")
    recentEditsBuffer: List[RecentEdit] = Field(default_factory=list, description="Rolling edit buffer.")
    recurrent_patterns: List[RecurrentPattern] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Compatibility properties for snake_case access
    @property
    def average_sentence_length(self) -> float:
        return self.baselineGenome.avgSentenceLength

    @property
    def burstiness_baseline(self) -> float:
        return self.baselineGenome.sentenceLengthVariance

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "userId": "660c1bf6e4b09d2f8832a101",
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
                "exemplars": ["Example response 1", "Example response 2"],
                "recentEditsBuffer": [],
            }
        },
    }
