import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Scheme Category Rules Schemas
# ============================================================================

class SchemeCategoryRuleBase(BaseModel):
    category: str = Field(..., description="Category: 'SC', 'ST', 'OBC', 'General', 'EWS', or 'All'")
    condition_name: str = Field(..., description="Condition title (e.g. Income Ceiling for OBC)")
    field: str = Field(..., description="Target citizen evaluation field (e.g. annual_family_income, age)")
    operator: str = Field(default="lte", description="Deterministic operator: lte, gte, eq, in, contains")
    expected_value: Any = Field(..., description="Expected threshold or value list")
    special_conditions: Optional[str] = Field(None, description="Category-specific relaxations, quotas, or additional mandates")
    exceptions: Optional[str] = Field(None, description="Statutory exceptions or disqualifications")
    effective_date: Optional[datetime] = None
    official_source_reference: Optional[str] = None
    geographic_scope: str = Field(default="National", description="Geographic scope: National, State: Maharashtra, State: Gujarat, etc.")
    verification_status: str = Field(default="Verified", description="Verification status: 'Verified', 'Review Required', 'Pending Verification'")


class SchemeCategoryRuleCreate(SchemeCategoryRuleBase):
    scheme_id: uuid.UUID


class SchemeCategoryRuleResponse(SchemeCategoryRuleBase):
    id: uuid.UUID
    scheme_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryRuleEvaluationRequest(BaseModel):
    category: str = Field(..., description="Caste / category provided on-demand with consent (e.g. 'OBC', 'SC', 'ST', 'General', 'EWS')")
    profile_data: Dict[str, Any] = Field(default_factory=dict, description="Citizen profile attributes evaluated on-demand without persistent storage")


class CategoryRuleEvaluationItem(BaseModel):
    condition_name: str
    field: str
    operator: str
    expected_value: Any
    actual_value: Optional[Any] = None
    is_satisfied: bool
    explanation: str


class CategoryRuleEvaluationResponse(BaseModel):
    scheme_id: uuid.UUID
    category: str
    is_category_eligible: bool
    evaluations: List[CategoryRuleEvaluationItem]
    special_notes: List[str] = Field(default_factory=list)
    advisory_disclaimer: str = (
        "This evaluation is strictly advisory and conducted on-demand. "
        "Category information is not stored in your permanent profile to protect your privacy."
    )


# ============================================================================
# Scheme Category Documents Schemas
# ============================================================================

class SchemeCategoryDocumentBase(BaseModel):
    category: str = Field(..., description="Target category: 'SC', 'ST', 'OBC', 'General', 'EWS', 'All'")
    document_name: str = Field(..., description="Name of the document required")
    document_type: str = Field(..., description="Standardized document type key: income_certificate, caste_certificate, etc.")
    is_mandatory: bool = Field(default=True, description="Whether the document is mandatory or optional")
    conditions_description: Optional[str] = None
    issuing_authority: str = Field(default="Competent Revenue Authority / Tahsildar / SDM")
    accepted_formats: str = Field(default="PDF, JPG, PNG")
    validity_rules: Optional[str] = Field(None, description="e.g. Current Financial Year, Permanent")
    official_source: Optional[str] = None


class SchemeCategoryDocumentCreate(SchemeCategoryDocumentBase):
    scheme_id: uuid.UUID


class SchemeCategoryDocumentResponse(SchemeCategoryDocumentBase):
    id: uuid.UUID
    scheme_id: uuid.UUID
    has_guide: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Document Guide Schemas
# ============================================================================

class DocumentGuideBase(BaseModel):
    document_type: str = Field(..., description="Unique document type key: income_certificate, caste_certificate, etc.")
    document_name: str = Field(..., description="Full bilingual document title")
    description: str = Field(..., description="Detailed description and statutory purpose")
    issuing_department: str = Field(..., description="Central or State issuing authority department")
    state_specific_authority: Dict[str, str] = Field(default_factory=dict, description="State-wise issuing authority map")
    required_supporting_documents: List[str] = Field(default_factory=list, description="List of required supporting proofs")
    online_steps: Dict[str, List[str]] = Field(default_factory=dict, description="Multilingual step-by-step online guidance {'en': [...], 'hi': [...], 'gu': [...]}")
    offline_steps: Dict[str, List[str]] = Field(default_factory=dict, description="Multilingual physical office guidance {'en': [...], 'hi': [...], 'gu': [...]}")
    fees_and_timelines: Dict[str, Any] = Field(default_factory=dict, description="Statutory fees and SLA processing days under Public Services Act")
    official_links: Dict[str, str] = Field(default_factory=dict, description="Verified portal links: application_portal, department_portal, tracking_portal")
    languages_supported: List[str] = Field(default_factory=lambda: ["en", "hi", "gu"])


class DocumentGuideCreate(DocumentGuideBase):
    pass


class DocumentGuideResponse(DocumentGuideBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentGuideSummaryResponse(BaseModel):
    id: uuid.UUID
    document_type: str
    document_name: str
    description: str
    issuing_department: str
    languages_supported: List[str]

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Scheme Analytics Schemas
# ============================================================================

class SchemeAnalyticsBreakdownBase(BaseModel):
    dimension: str = Field(..., description="Dimension: 'caste_category', 'state', 'district', 'gender', 'yearly_trend'")
    category_name: str = Field(..., description="Slice label: 'SC', 'ST', 'OBC', 'General', 'EWS', 'Maharashtra', etc.")
    metric_value: int = Field(default=0, description="Metric count")
    percentage: Optional[float] = Field(None, description="Proportion within dimension (0-100%)")
    notes: Optional[str] = None


class SchemeAnalyticsBreakdownCreate(SchemeAnalyticsBreakdownBase):
    pass


class SchemeAnalyticsBreakdownResponse(SchemeAnalyticsBreakdownBase):
    id: uuid.UUID
    dataset_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class SchemeAnalyticsDatasetBase(BaseModel):
    source_name: str = Field(..., description="Official government source name (e.g. Ministry Dashboard, Standing Committee Report)")
    report_title: Optional[str] = Field(None, description="Official report or publication document title")
    source_url: str = Field(..., description="Official portal or report URL")
    source_publication_date: Optional[datetime] = None
    reporting_period: str = Field(..., description="Reporting period (e.g. 'FY 2023-24', '16th Installment')")
    geographic_scope: str = Field(default="National", description="Geographic scope: National, State: Maharashtra, State: Gujarat, etc.")
    metric_type: str = Field(default="unique_beneficiaries", description="Metric definition: unique_beneficiaries, households, etc.")
    metric_definition: Optional[str] = Field(None, description="Exact operational definition of metric e.g. cumulative verified farmers, sanctioned houses")
    total_beneficiaries: int = Field(default=0, description="Total verified aggregate beneficiary count")
    notes: Optional[str] = None


class SchemeAnalyticsDatasetCreate(SchemeAnalyticsDatasetBase):
    scheme_id: uuid.UUID
    breakdowns: List[SchemeAnalyticsBreakdownCreate] = Field(default_factory=list)


class SchemeAnalyticsDatasetResponse(SchemeAnalyticsDatasetBase):
    id: uuid.UUID
    scheme_id: uuid.UUID
    dataset_version: int
    verification_status: str
    is_published: bool
    published_at: Optional[datetime] = None
    last_verified_at: Optional[datetime] = None
    breakdowns: List[SchemeAnalyticsBreakdownResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    civic_disclaimer: str = (
        "Official Government Aggregate Data. Sourced exclusively from official government reports "
        "and public administrative dashboards. This data is strictly independent of JanMitra Assist registered users."
    )

    model_config = ConfigDict(from_attributes=True)


class SchemeAnalyticsImportRequest(BaseModel):
    source_name: str
    report_title: Optional[str] = None
    source_url: str
    reporting_period: str
    geographic_scope: str = "National"
    metric_type: str = "unique_beneficiaries"
    metric_definition: Optional[str] = None
    total_beneficiaries: int
    notes: Optional[str] = None
    breakdowns: List[SchemeAnalyticsBreakdownCreate] = Field(default_factory=list)


class SchemeAnalyticsAuditLogResponse(BaseModel):
    id: uuid.UUID
    dataset_id: Optional[uuid.UUID] = None
    scheme_id: Optional[uuid.UUID] = None
    admin_id: Optional[uuid.UUID] = None
    action: str
    details: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

