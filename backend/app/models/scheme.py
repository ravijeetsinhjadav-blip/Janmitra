import uuid
from sqlalchemy import Column, String, Text, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class Scheme(Base):
    """Government service / welfare scheme repository entity.
    
    Contains scheme metadata, official source links, and application URLs.
    Does not replace government portals; users are directed to official_application_url.
    """
    __tablename__ = "schemes"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary UUID key for government scheme",
    )
    scheme_name = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Official title of the government scheme",
    )
    description = Column(
        Text,
        nullable=False,
        comment="Detailed overview of objectives, benefits, and coverage",
    )
    short_description = Column(
        String(500),
        nullable=True,
        comment="Concise single-paragraph summary for mobile cards",
    )
    category = Column(
        String(100),
        nullable=False,
        default="General",
        index=True,
        comment="Sector category: Agriculture, Healthcare, Education, Housing, etc.",
    )
    department = Column(
        String(200),
        nullable=False,
        index=True,
        comment="Nodal ministry or state department administering the scheme",
    )
    state_applicability = Column(
        String(100),
        nullable=False,
        default="All India",
        index=True,
        comment="Geographic scope: 'All India' or specific State/UT name",
    )
    eligibility_summary = Column(
        Text,
        nullable=False,
        comment="Summary of eligibility criteria (age, income, occupation, etc.)",
    )
    benefits = Column(
        JSONB,
        nullable=False,
        default=list,
        comment="List of financial and material benefits as JSONB array",
    )
    eligibility_criteria = Column(
        JSONB,
        nullable=False,
        default=list,
        comment="Structured rule conditions evaluated deterministically by the eligibility engine",
    )
    required_profile_fields = Column(
        JSONB,
        nullable=False,
        default=list,
        comment="List of citizen profile field names required for complete evaluation",
    )
    application_process = Column(
        JSONB,
        nullable=False,
        default=list,
        comment="Step-by-step guidance on how citizen completes application on government portal",
    )
    required_documents = Column(
        JSONB,
        nullable=False,
        default=list,
        comment="Informational checklist of official documentation required",
    )
    official_source_url = Column(
        String(500),
        nullable=False,
        comment="Official government portal guideline / gazette URL",
    )
    official_application_url = Column(
        String(500),
        nullable=False,
        comment="Official government online portal URL for actual submission",
    )
    source_last_verified_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when scheme source information was last verified",
    )
    status = Column(
        String(20),
        nullable=False,
        default="active",
        index=True,
        comment="Scheme status: 'active', 'inactive', 'discontinued'",
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Flag indicating whether scheme is currently accepting applications",
    )
    is_demo_data = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Flag designating demo / test seed data vs live government records",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Scheme record creation timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Scheme record last updated timestamp",
    )

    # Relationships
    assessments = relationship("Assessment", back_populates="scheme")
    applications = relationship("Application", back_populates="scheme")

    def __repr__(self) -> str:
        return f"<Scheme id={self.id} name='{self.scheme_name}' state='{self.state_applicability}'>"

