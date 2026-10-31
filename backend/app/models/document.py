import uuid
from sqlalchemy import Column, String, Integer, BigInteger, Float, Boolean, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


# OCR Processing Lifecycle Constants
class DocumentProcessingStatus:
    UPLOADED = "UPLOADED"
    PENDING_OCR = "PENDING_OCR"
    PROCESSING = "PROCESSING"
    OCR_COMPLETED = "OCR_COMPLETED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    OCR_FAILED = "OCR_FAILED"


class DocumentMetadata(Base):
    """Metadata tracking citizen documents for eligibility verification.
    
    Privacy & Storage Architecture Rules:
    1. Binary files are strictly stored on secure disk/object storage (referenced via storage_reference).
    2. Document binary contents are NEVER stored in PostgreSQL.
    3. Document content is accessed only through authorized, authenticated endpoints verifying user ownership.
    4. No raw file bytes or unmasked citizen PII are dumped to plain logs.
    """
    __tablename__ = "document_metadata"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary UUID key for document record",
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owner citizen user ID",
    )
    document_type = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Document classification (e.g., income_certificate, caste_certificate, domicile, ration_card, aadhaar_card)",
    )
    original_filename = Column(
        String(255),
        nullable=False,
        comment="Original uploaded filename (sanitized)",
    )
    storage_reference = Column(
        String(500),
        nullable=False,
        comment="Storage path or identifier on secure filesystem / object store",
    )
    mime_type = Column(
        String(100),
        nullable=False,
        comment="MIME type (e.g., application/pdf, image/jpeg, image/png)",
    )
    file_size = Column(
        BigInteger,
        nullable=False,
        comment="Document file size in bytes",
    )
    upload_status = Column(
        String(50),
        nullable=False,
        default="uploaded",
        index=True,
        comment="Status: uploaded, pending_ocr, verified, rejected",
    )

    # Phase 5: OCR Processing & Intelligence Fields
    ocr_status = Column(
        String(50),
        nullable=False,
        default=DocumentProcessingStatus.UPLOADED,
        index=True,
        comment="Status: UPLOADED, PENDING_OCR, PROCESSING, OCR_COMPLETED, MANUAL_REVIEW_REQUIRED, OCR_FAILED",
    )
    ocr_extracted_text = Column(
        Text,
        nullable=True,
        comment="Full extracted text from OCR engine",
    )
    ocr_confidence = Column(
        Float,
        nullable=True,
        comment="OCR extraction confidence score (0.0 to 1.0)",
    )
    ocr_metadata = Column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Structured OCR metadata: page count, detected language, block bounding boxes, words, lines, etc.",
    )
    ocr_completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when OCR extraction was completed",
    )
    manual_review_required = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Flag indicating document requires manual citizen/operator review (e.g. low OCR confidence, ambiguous text)",
    )
    ocr_error_message = Column(
        String(500),
        nullable=True,
        comment="Error description if OCR processing encountered a failure",
    )
    processing_token = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Ownership lease token identifying active processing attempt",
    )
    lease_expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Lease expiration timestamp for in-flight OCR execution",
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Upload registration timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Metadata last update timestamp",
    )

    # Relationships
    user = relationship("User", back_populates="documents")

    def __init__(self, **kwargs):
        kwargs.setdefault("ocr_status", DocumentProcessingStatus.UPLOADED)
        kwargs.setdefault("ocr_metadata", {})
        kwargs.setdefault("manual_review_required", False)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<DocumentMetadata id={self.id} user_id={self.user_id} type='{self.document_type}' ocr_status='{self.ocr_status}'>"


