from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ConditionAnalysisItem(BaseModel):
    """Evaluation summary of a single scheme condition."""
    condition: str
    status: str
    note: str


class CitationItem(BaseModel):
    """Citation of an official government guideline or legal provision."""
    title: str
    source_title: str
    source_reference: Optional[str] = None
    source_url: str
    source_freshness_status: str
    is_demo_data: bool = True


class ReadinessBreakdown(BaseModel):
    """Multi-dimensional application readiness metrics."""
    overall_readiness_score: float = Field(..., description="Weighted composite readiness score (0-100%). Not approval probability.")
    criteria_match_percentage: float = Field(..., description="Proportion of verified conditions satisfied (0-100%).")
    document_coverage_percentage: float = Field(..., description="Proportion of required document types present (0-100%).")
    information_completeness_percentage: float = Field(..., description="Proportion of required fields present in profile (0-100%).")
    consistency_score: float = Field(..., description="Document-profile consistency score (0-100%).")
    consistency_status: str = Field(..., description="'Consistent', 'Discrepancy Detected', or 'Review Required'")
    score_interpretation: str
    uploaded_document_types: List[str] = Field(default_factory=list)
    missing_document_types: List[str] = Field(default_factory=list)
    discrepancies: List[str] = Field(default_factory=list)
    low_confidence_documents: List[str] = Field(default_factory=list)


class AIAdvisoryGuidance(BaseModel):
    """Structured AI-generated citizen advisory and preparation guidance."""
    summary: str
    assessment_explanation: str
    criteria_analysis: List[ConditionAnalysisItem] = Field(default_factory=list)
    document_analysis: str
    potential_inconsistencies: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    official_portal_guidance: str
    citations: List[CitationItem] = Field(default_factory=list)
    language: str = "en"
    is_mock: bool = False
    disclaimer: str = (
        "Advisory Notice: This guidance is AI-assisted and based on citizen-provided details. "
        "It does NOT constitute an official government determination or guarantee approval."
    )


class AdvisoryAssessmentResponse(BaseModel):
    """Comprehensive response combining deterministic result, readiness score, and AI advisory."""
    assessment_id: UUID
    scheme_id: UUID
    scheme_name: str
    category: str
    overall_status: str
    readiness: ReadinessBreakdown
    advisory: AIAdvisoryGuidance
    evaluated_at: datetime
    official_source_url: str
    official_application_url: str

    model_config = ConfigDict(from_attributes=True)


class AdvisoryRequest(BaseModel):
    """Citizen request parameters for AI advisory generation."""
    language: Optional[str] = Field(default="en", description="Language code: 'en', 'hi', or 'gu'")
