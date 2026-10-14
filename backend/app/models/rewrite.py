"""
InkFlow Rewrite Domain Models and Schemas.

================================================================================
Architecture and Design Rationale:
--------------------------------------------------------------------------------
This module encapsulates all schemas required by the 4-stage rewrite pipeline,
telemetry logs, evaluation metrics, and client responses adhering to:
- docs/backend.md Section 4 (4-Stage Sequential Quality Pipeline)
- docs/backend.md Section 7 (`rewrites` Collection Schema)
- docs/backend.md Section 8 (REST API Endpoints Specification)
================================================================================
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict, AliasChoices


class InputType(str, Enum):
    RAW_DRAFT = "raw_draft"
    BULLET_POINTS = "bullet_points"


class RewriteContext(str, Enum):
    WORK_FORMAL = "work_formal"
    ACADEMIC = "academic"
    CHAT = "chat"
    EXECUTIVE = "executive"
    PROFESSIONAL = "professional"


class RewriteRequest(BaseModel):
    """
    Input payload submitted by client to transform text.
    Specified in backend.md Section 8:
    { input: string, inputType: "raw_draft" | "bullet_points", context: "work_formal" | "academic" | "chat" }
    """
    input: Optional[str] = Field(None, description="The draft text or bullet points.")
    text: Optional[str] = Field(None, description="Backward-compatible alias for input.")
    inputType: InputType = Field(default=InputType.RAW_DRAFT, description="Source type.")
    context: Optional[str] = Field("work_formal", description="Context profile identifier.")
    target_tone: Optional[str] = Field(None, description="Backward-compatible alias for context.")
    preserve_quirks: bool = Field(default=True, description="Preserve em-dashes and commas.")

    def get_raw_input(self) -> str:
        """Returns the primary text input regardless of whether input or text was used."""
        return (self.input or self.text or "").strip()

    def get_context(self) -> str:
        """Returns target context or tone."""
        return (self.context or self.target_tone or "work_formal").strip()

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "input": "Furthermore, it is a testament to our dedication that we delve into the tapestry of solutions.",
                "inputType": "raw_draft",
                "context": "work_formal",
            }
        },
    }


class RewriteStageLog(BaseModel):
    """
    Audit log documenting latency, provider, and intermediate text for a single stage.
    """
    stage: str = Field(..., description="Pipeline stage identifier.")
    input_text: str = Field(..., description="Text entering the stage.")
    output_text: str = Field(..., description="Text exiting the stage.")
    duration_ms: float = Field(..., description="Wall-clock execution time in milliseconds.")
    provider_used: str = Field(..., description="LLM provider servicing this stage.")
    status: str = Field(default="success", description="Execution status ('success', 'retried', 'warning').")
    notes: Optional[str] = Field(None, description="Diagnostic rationale.")


class StageOutputs(BaseModel):
    """
    Intermediate output logs across all 4 stages adhering to backend.md Section 7.
    """
    stage1_generate: str = Field(default="", description="Stage 1 output.")
    stage2_tone_transform: str = Field(default="", description="Stage 2 output.")
    stage3_meaning_checked: bool = Field(default=True, description="Passed meaning check gate.")
    stage3_retried: bool = Field(default=False, description="Whether Stage 2 was retried.")
    stage3_drift_reason: Optional[str] = Field(default=None, description="Drift reason if retried.")
    stage4_grammar_passed: str = Field(default="", description="Stage 4 final output.")


class EvalsReport(BaseModel):
    """
    Quantitative metrics evaluating transformation quality and anti-slop efficacy.
    """
    model_config = ConfigDict(populate_by_name=True)

    slopReductionScore: float = Field(
        ...,
        validation_alias=AliasChoices("slopReductionScore", "slop_reduction_score"),
        serialization_alias="slopReductionScore",
        ge=0.0,
        le=100.0,
        description="Slop cleanliness score (0-100%).",
    )
    styleAlignmentScore: float = Field(
        ...,
        validation_alias=AliasChoices("styleAlignmentScore", "style_alignment_score"),
        serialization_alias="styleAlignmentScore",
        ge=0.0,
        le=100.0,
        description="Style alignment score (0-100%).",
    )
    semanticFidelityScore: float = Field(
        ...,
        validation_alias=AliasChoices("semanticFidelityScore", "semantic_fidelity_score"),
        serialization_alias="semanticFidelityScore",
        ge=0.0,
        le=100.0,
        description="Factual retention score (0-100%).",
    )
    burstinessVariance: float = Field(
        ...,
        validation_alias=AliasChoices("burstinessVariance", "burstiness_variance"),
        serialization_alias="burstinessVariance",
        ge=0.0,
        description="Sentence length variance.",
    )

    # Compatibility properties for snake_case
    @property
    def slop_reduction_score(self) -> float:
        return self.slopReductionScore if self.slopReductionScore <= 1.0 else round(self.slopReductionScore / 100.0, 3)

    @slop_reduction_score.setter
    def slop_reduction_score(self, value: float) -> None:
        self.slopReductionScore = value

    @property
    def style_alignment_score(self) -> float:
        return self.styleAlignmentScore if self.styleAlignmentScore <= 1.0 else round(self.styleAlignmentScore / 100.0, 3)

    @style_alignment_score.setter
    def style_alignment_score(self, value: float) -> None:
        self.styleAlignmentScore = value

    @property
    def semantic_fidelity_score(self) -> float:
        return self.semanticFidelityScore if self.semanticFidelityScore <= 1.0 else round(self.semanticFidelityScore / 100.0, 3)

    @semantic_fidelity_score.setter
    def semantic_fidelity_score(self, value: float) -> None:
        self.semanticFidelityScore = value

    @property
    def burstiness_variance(self) -> float:
        return self.burstinessVariance

    @burstiness_variance.setter
    def burstiness_variance(self, value: float) -> None:
        self.burstinessVariance = value


class RewriteResponse(BaseModel):
    """
    Response schema delivered by POST /api/v1/rewrite/pipeline adhering to backend.md Section 8.
    {
      "finalOutput": string,
      "meaningCheckFailed": bool,
      "meaningWarning": string | null,
      "provider": string,
      "evalScores": dict
    }
    """
    finalOutput: str = Field(..., description="Anti-slop rewritten output text.")
    meaningCheckFailed: bool = Field(default=False, description="Soft warning flag for meaning drift.")
    meaningWarning: Optional[str] = Field(default=None, description="Amber warning badge text if failed.")
    provider: str = Field(..., description="LLM provider: 'groq_llama33' or 'groq_llama31_8b'.")
    evalScores: EvalsReport = Field(..., description="Evaluations report.")
    stageOutputs: Optional[StageOutputs] = Field(default=None, description="Detailed stage outputs.")
    stages: List[RewriteStageLog] = Field(default_factory=list, description="Telemetry logs.")
    words_consumed: int = Field(default=0, description="Words deducted from user quota.")
    quota_remaining: int = Field(default=2500, description="Remaining word quota this week.")
    rewrite_id: Optional[str] = Field(default=None, description="MongoDB ObjectId of rewrite record.")

    # Backward compatibility properties
    @property
    def original_text(self) -> str:
        return self.finalOutput

    @property
    def rewritten_text(self) -> str:
        return self.finalOutput

    @property
    def provider_used(self) -> str:
        return self.provider

    @property
    def evals(self) -> EvalsReport:
        return self.evalScores

    @property
    def meaning_warning(self) -> Optional[str]:
        return self.meaningWarning


class RewriteAcceptRequest(BaseModel):
    """
    Request schema for POST /api/v1/rewrite/accept adhering to backend.md Section 8:
    { rewriteId: string, finalUserText: string }
    """
    rewriteId: str = Field(..., description="Identifier of the rewrite record.")
    finalUserText: str = Field(..., description="Final text accepted or edited by author.")
