import uuid
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class SchemeKnowledgeChunk(Base):
    """Structured knowledge chunk from official government scheme documentation.
    
    Used for Retrieval-Augmented Generation (RAG) to ensure the AI advisory engine
    makes only verifiable, factual claims supported by authoritative nodal sources.
    """
    __tablename__ = "scheme_knowledge_chunks"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary UUID key for knowledge chunk",
    )
    scheme_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schemes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated scheme UUID",
    )
    chunk_title = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Concise section/clause title (e.g. Landholding Limits, Required Certificates)",
    )
    chunk_category = Column(
        String(50),
        nullable=False,
        default="eligibility",
        index=True,
        comment="Category: eligibility, documents, benefits, process, or faq",
    )
    chunk_content = Column(
        Text,
        nullable=False,
        comment="Authoritative verbatim or summarized text excerpt from official scheme rules",
    )
    source_url = Column(
        String(500),
        nullable=False,
        comment="Official government portal URL where this clause is published",
    )
    source_title = Column(
        String(255),
        nullable=False,
        comment="Title of official government publication or guideline document",
    )
    source_reference = Column(
        String(255),
        nullable=True,
        comment="Specific chapter, clause, or paragraph reference in official document",
    )
    source_freshness_status = Column(
        String(50),
        nullable=False,
        default="Verified Official Source",
        comment="Freshness status: Verified Official Source, Pending Verification, Review Required, Stale",
    )
    is_demo_data = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Distinguishes curated MCA demo chunks from live production government scrapes",
    )
    embedding = Column(
        JSONB,
        nullable=True,
        comment="Dense vector representation stored as JSON float array for semantic ranking",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when chunk was ingested",
    )

    # Relationships
    scheme = relationship("Scheme", back_populates="knowledge_chunks")

    def __repr__(self) -> str:
        return f"<SchemeKnowledgeChunk id={self.id} scheme_id={self.scheme_id} title='{self.chunk_title[:30]}'>"
