from uuid import UUID
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class DocumentPreparationStatusItem(BaseModel):
    """Document preparation status classification."""
    document_name: str = Field(..., description="Document type name required by the scheme")
    status: str = Field(
        ...,
        description="Preparation status: Ready for Application Preparation, Available, Missing, Manual Review Required, Needs Correction, Processing Failed",
    )
    notes: str = Field(default="", description="Preparation notes and OCR verification feedback")
    matching_document_id: Optional[UUID] = Field(default=None, description="UUID of matching vault document if present")


class ChecklistItem(BaseModel):
    """Actionable application preparation checklist item."""
    item_id: str = Field(..., description="Unique deterministic identifier for the checklist item")
    category: str = Field(
        ...,
        description="Category: document, profile_field, declaration, portal_action",
    )
    title: str = Field(..., description="Short title of the preparation requirement")
    description: str = Field(..., description="Detailed preparation instruction or explanation")
    is_mandatory: bool = Field(default=True, description="Whether this requirement is strictly mandatory for the scheme")
    is_completed: bool = Field(default=False, description="Whether the citizen has marked this preparation step as completed")


class ApplicantInfoRequirement(BaseModel):
    """Specific demographic or administrative fact required during portal filing."""
    field_name: str = Field(..., description="Name of the attribute or question on the portal")
    description: str = Field(..., description="What information is requested and where to find it")
    importance: str = Field(default="Mandatory", description="Importance level: Mandatory, Highly Recommended, Optional")


class SupportingDocumentSpecification(BaseModel):
    """Official documentary requirements including issuing authorities and validity periods."""
    document_type: str = Field(..., description="Document type")
    specifications: str = Field(..., description="Acceptable formats, size limits, and validity period")
    issuing_authority: str = Field(..., description="Recognized issuing government authority")


class PortalStepInstruction(BaseModel):
    """Sequence of official portal registration and filing steps."""
    step_number: int = Field(..., description="Step sequence number")
    title: str = Field(..., description="Step title")
    instruction: str = Field(..., description="Detailed filing instruction")


class ApplicationInfoGuide(BaseModel):
    """Scheme-specific comprehensive application preparation information guide."""
    applicant_info_required: List[ApplicantInfoRequirement] = Field(default_factory=list)
    supporting_documents_specs: List[SupportingDocumentSpecification] = Field(default_factory=list)
    important_declarations: List[str] = Field(default_factory=list)
    common_mistakes_to_avoid: List[str] = Field(default_factory=list)
    submission_precautions: List[str] = Field(default_factory=list)
    portal_steps: List[PortalStepInstruction] = Field(default_factory=list)
    language: str = Field(default="en", description="Guidance language code: en, hi, gu")
    disclaimer: str = Field(
        default="AI-assisted guidance does not constitute an official government determination or guarantee application approval.",
        description="Statutory non-guarantee advisory notice",
    )


class ApplicationAssistanceRequest(BaseModel):
    """Request payload to initiate or regenerate application assistance."""
    language: Optional[str] = Field(default="en", description="Preferred guidance language code (en, hi, gu)")


class ChecklistItemToggleRequest(BaseModel):
    """Request payload to mark a preparation checklist item as completed or pending."""
    is_completed: bool = Field(..., description="New completion status for the checklist item")


class ChecklistUpdateResponse(BaseModel):
    """Response returned upon toggling a preparation checklist item."""
    item_id: str
    is_completed: bool
    completed_count: int
    total_count: int
    completion_percentage: float
    message: str = "Checklist progress updated. This preparation checklist does NOT submit your application to the government."


class ApplicationAssistanceResponse(BaseModel):
    """Comprehensive personalized application assistance and preparation response."""
    scheme_id: UUID
    scheme_name: str
    category: str
    department: str
    assessment_id: Optional[UUID] = None
    overall_status: str
    criteria_match_percentage: float
    overall_readiness_score: float
    readiness_interpretation: str
    document_preparation_statuses: List[DocumentPreparationStatusItem] = Field(default_factory=list)
    checklist: List[ChecklistItem] = Field(default_factory=list)
    checklist_completed_count: int = 0
    checklist_total_count: int = 0
    checklist_completion_percentage: float = 0.0
    guide: ApplicationInfoGuide
    official_application_url: str
    official_source_url: str
    is_demo_data: bool = True
    language: str = "en"
    evaluated_at: datetime
    disclaimer: str = (
        "Advisory Notice: JanMitra Assist is an application preparation assistant. "
        "It does NOT replace official government portals or submit applications on your behalf. "
        "Guidance does not guarantee official approval."
    )


class AdvancedCompletenessResponse(BaseModel):
    """Premium-exclusive application completeness and optimization analysis."""
    scheme_id: UUID
    is_premium_analysis: bool = True
    completeness_score: float
    field_gap_analysis: List[Dict[str, Any]] = Field(default_factory=list)
    document_readiness_optimizations: List[str] = Field(default_factory=list)
    expedited_action_plan: List[str] = Field(default_factory=list)
    disclaimer: str = (
        "Premium Completeness Analysis: Identifies preparation gaps prior to portal submission. "
        "It does not guarantee government scheme approval."
    )


class ApplicationPreparationPacketResponse(BaseModel):
    """Consolidated, printable/downloadable summary of scheme application preparation.
    Strictly contains no PII, Aadhaar numbers, or raw OCR tokens.
    """
    scheme_id: UUID
    scheme_name: str
    department: str
    category: str
    official_source_url: str
    official_application_url: str
    generated_at: datetime
    language: str = "en"
    criteria_match_percentage: float
    readiness_score: float
    document_statuses: List[DocumentPreparationStatusItem] = Field(default_factory=list)
    checklist: List[ChecklistItem] = Field(default_factory=list)
    portal_steps: List[PortalStepInstruction] = Field(default_factory=list)
    common_mistakes: List[str] = Field(default_factory=list)
    precautions: List[str] = Field(default_factory=list)
    source_verification_details: Optional[str] = None
    statutory_disclaimer: str = (
        "Advisory Notice: JanMitra Assist is an application preparation assistant. "
        "It is not a government agency and does not submit applications on your behalf. "
        "Guidance does not guarantee official approval."
    )

