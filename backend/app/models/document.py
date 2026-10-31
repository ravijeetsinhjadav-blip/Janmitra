import uuid
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class DocumentMetadata(Base):
    """Metadata tracking citizen documents for eligibility verification.
    
    Privacy Architecture Rules:
    1. Binary files are strictly stored on disk/object storage (referenced via storage_reference).
    2. Document binary contents are NEVER stored in PostgreSQL.
    3. No document contents or PII extracted from OCR are logged.
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
        comment="Document classification (e.g., income_certificate, caste_certificate, domicile, ration_card)",
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

    def __repr__(self) -> str:
        return f"<DocumentMetadata id={self.id} user_id={self.user_id} type='{self.document_type}'>"
