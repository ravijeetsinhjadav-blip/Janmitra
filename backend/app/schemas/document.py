import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class DocumentMetadataBase(BaseModel):
    document_type: str = Field(..., description="Classification (e.g. income_certificate, caste_certificate, ration_card)")


class DocumentMetadataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    document_type: str
    original_filename: str
    storage_reference: str
    mime_type: str
    file_size: int
    upload_status: str
    ocr_status: str
    ocr_confidence: Optional[float] = None
    ocr_extracted_text: Optional[str] = None
    ocr_metadata: Dict[str, Any] = Field(default_factory=dict)
    ocr_completed_at: Optional[datetime] = None
    manual_review_required: bool = False
    ocr_error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    message: str = "Document uploaded and processed successfully."
    document: DocumentMetadataResponse


class DocumentListResponse(BaseModel):
    total: int
    documents: List[DocumentMetadataResponse]


class SchemeDocumentChecklistItem(BaseModel):
    document_type: str
    description: Optional[str] = None
    is_mandatory: bool = True
    is_uploaded: bool = False
    uploaded_document_id: Optional[uuid.UUID] = None
    ocr_status: Optional[str] = None
    manual_review_required: bool = False


class SchemeDocumentChecklistResponse(BaseModel):
    scheme_id: uuid.UUID
    scheme_name: str
    total_required: int
    total_uploaded: int
    is_fully_prepared: bool
    checklist: List[SchemeDocumentChecklistItem]
    disclaimer: str = (
        "Document presence in your JanMitra vault verifies readiness for official submission, "
        "but does not replace government verification or guarantee scheme approval."
    )
