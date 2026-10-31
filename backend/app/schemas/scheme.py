from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class EligibilityCondition(BaseModel):
    """Structured rule condition definition for a government scheme."""
    condition_name: str = Field(..., description="Human-readable condition title")
    field: str = Field(..., description="Target citizen profile field (e.g. age, state, annual_family_income, occupation, residence_type)")
    operator: str = Field(..., description="Deterministic operator: eq, neq, gt, gte, lt, lte, in, contains")
    expected_value: Any = Field(..., description="Value or list of values expected to satisfy the condition")
    explanation: str = Field(default="", description="Simple explanation for citizens")

    model_config = ConfigDict(from_attributes=True)


class ConditionEvaluation(BaseModel):
    """Evaluation result for an individual eligibility rule condition."""
    condition_name: str
    field: str
    operator: str
    expected_value: Any
    actual_value: Optional[Any] = None
    status: str = Field(..., description="Evaluation outcome: 'satisfied', 'not_satisfied', or 'unknown'")
    explanation: str

    model_config = ConfigDict(from_attributes=True)


class SchemeBase(BaseModel):
    """Base attributes for government welfare scheme."""
    scheme_name: str
    short_description: Optional[str] = None
    description: str
    department: str
    category: str = "General"
    state_applicability: str = "All India"
    eligibility_summary: str
    benefits: List[str] = Field(default_factory=list)
    eligibility_criteria: List[EligibilityCondition] = Field(default_factory=list)
    required_profile_fields: List[str] = Field(default_factory=list)
    application_process: List[str] = Field(default_factory=list)
    required_documents: List[str] = Field(default_factory=list)
    official_source_url: str
    official_application_url: str
    source_last_verified_at: Optional[datetime] = None
    source_verification_details: Optional[str] = None
    status: str = "active"
    is_active: bool = True
    is_demo_data: bool = False


class SchemeResponse(SchemeBase):
    """Public government scheme response schema."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    advisory_notice: str = (
        "JanMitra Assist is an advisory preparation platform. Information is gathered from "
        "official government sources. Final eligibility and approvals are made exclusively "
        "by competent government authorities on official portals."
    )

    model_config = ConfigDict(from_attributes=True)


class SchemeListResponse(BaseModel):
    """Paginated response for scheme discovery."""
    items: List[SchemeResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SchemeCategoryItem(BaseModel):
    """Scheme sector category with active scheme counts."""
    category: str
    count: int


class SchemeRecommendation(BaseModel):
    """Profile-based scheme recommendation for authenticated citizen."""
    scheme: SchemeResponse
    recommendation_reason: str
    criteria_match_percentage: float = Field(..., description="Proportion of evaluated conditions satisfied based on profile (0-100%). Not an approval probability.")
    match_score: float = Field(..., description="Alias for criteria_match_percentage for backward compatibility")
    satisfied_count: int
    unknown_count: int
    missing_profile_fields: List[str] = Field(default_factory=list)
    advisory_notice: str = (
        "Recommendations are advisory suggestions based solely on your entered profile "
        "and do not guarantee eligibility or official government approval."
    )


class AssessmentResultResponse(BaseModel):
    """Structured advisory outcome of deterministic eligibility assessment."""
    assessment_id: UUID
    scheme_id: UUID
    scheme_name: str
    category: str
    overall_status: str = Field(
        ...,
        description="'Potentially Eligible', 'Not Eligible Based on Available Information', or 'Insufficient Information'",
    )
    criteria_match_percentage: float = Field(..., description="Proportion of verified conditions satisfied (0.0 to 100.0). Not an approval likelihood.")
    overall_readiness_score: float = Field(..., description="Alias for criteria_match_percentage for backward compatibility")
    score_interpretation: str = Field(
        default=(
            "Criteria Match Percentage indicates the proportion of predefined scheme conditions "
            "that are verified as satisfied based on your profile. It does NOT represent a probability "
            "or guarantee of official government approval."
        ),
        description="Clear explanation of score interpretation",
    )
    conditions_breakdown: List[ConditionEvaluation]
    satisfied_count: int
    not_satisfied_count: int
    unknown_count: int
    missing_fields: List[str]
    official_source_url: str
    official_application_url: str
    evaluated_at: datetime
    advisory_disclaimer: str = (
        "This assessment is strictly advisory and does not constitute official government approval or rejection. "
        "Citizens must complete formal applications on the official government portal."
    )

    model_config = ConfigDict(from_attributes=True)


class AssessmentHistoryItem(BaseModel):
    """Summary item in citizen's assessment history."""
    assessment_id: UUID
    scheme_id: Optional[UUID] = None
    scheme_name: str
    overall_status: str
    criteria_match_percentage: float
    overall_readiness_score: float
    satisfied_count: int
    not_satisfied_count: int
    unknown_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
