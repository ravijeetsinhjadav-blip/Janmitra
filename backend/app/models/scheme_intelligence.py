import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    Integer,
    BigInteger,
    Float,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class SchemeCategoryRule(Base):
    """Category / caste-specific eligibility rule for a welfare scheme.
    
    Captures official criteria variations across SC, ST, OBC, General, EWS, etc.
    """
    __tablename__ = "scheme_category_rules"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary UUID key for category eligibility rule",
    )
    scheme_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schemes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key referencing parent scheme",
    )
    category = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Category: 'SC', 'ST', 'OBC', 'General', 'EWS', or 'All'",
    )
    condition_name = Column(
        String(255),
        nullable=False,
        comment="Human-readable title of the category condition",
    )
    field = Column(
        String(100),
        nullable=False,
        comment="Target evaluation field: annual_family_income, age, occupation, etc.",
    )
    operator = Column(
        String(20),
        nullable=False,
        default="lte",
        comment="Deterministic comparison operator: lte, gte, eq, in, contains",
    )
    expected_value = Column(
        JSONB,
        nullable=False,
        comment="Expected threshold value or list of values",
    )
    special_conditions = Column(
        Text,
        nullable=True,
        comment="Category-specific relaxations, quotas, or additional mandates",
    )
    exceptions = Column(
        Text,
        nullable=True,
        comment="Statutory exceptions or disqualifications",
    )
    effective_date = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Official notification / gazette effective date",
    )
    official_source_reference = Column(
        String(500),
        nullable=True,
        comment="Official guideline section citation",
    )
    geographic_scope = Column(
        String(100),
        nullable=False,
        default="National",
        server_default="National",
        comment="Geographic scope: National, State: Maharashtra, State: Gujarat, etc.",
    )
    verification_status = Column(
        String(50),
        nullable=False,
        default="Verified",
        server_default="Verified",
        comment="Verification status: 'Verified', 'Review Required', 'Pending Verification'",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship
    scheme = relationship("Scheme", backref="category_rules")


class SchemeCategoryDocument(Base):
    """Category-specific document checklist requirement for a welfare scheme.
    
    Defines mandatory and conditional certificates required per category.
    """
    __tablename__ = "scheme_category_documents"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary UUID key for category document rule",
    )
    scheme_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schemes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key referencing parent scheme",
    )
    category = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Target category: 'SC', 'ST', 'OBC', 'General', 'EWS', 'All'",
    )
    document_name = Column(
        String(255),
        nullable=False,
        comment="Document name (e.g. Caste Certificate, Income Certificate, EWS Certificate)",
    )
    document_type = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Standardized vault classification key: caste_certificate, income_certificate, ews_certificate, etc.",
    )
    is_mandatory = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether the document is mandatory or optional/conditional",
    )
    conditions_description = Column(
        Text,
        nullable=True,
        comment="Conditions under which this document is required",
    )
    issuing_authority = Column(
        String(255),
        nullable=False,
        default="Competent Revenue Authority / Tahsildar / SDM",
        comment="Statutory issuing authority",
    )
    accepted_formats = Column(
        String(100),
        nullable=False,
        default="PDF, JPG, PNG",
        comment="Accepted file formats",
    )
    validity_rules = Column(
        String(255),
        nullable=True,
        comment="Validity period (e.g. Current Financial Year, 3 Years, Permanent)",
    )
    official_source = Column(
        String(500),
        nullable=True,
        comment="Official document checklist citation",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    scheme = relationship("Scheme", backref="category_documents")


class DocumentGuide(Base):
    """Detailed step-by-step guidance for obtaining an official certificate or document.
    
    Explains issuing authority, required supporting documents, online steps, offline steps,
    statutory fees, and official application/tracking links.
    """
    __tablename__ = "document_guides"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary UUID key for document guide",
    )
    document_type = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique document identifier key: income_certificate, caste_certificate, domicile_certificate, ews_certificate, etc.",
    )
    document_name = Column(
        String(255),
        nullable=False,
        comment="Full title in English and regional languages",
    )
    description = Column(
        Text,
        nullable=False,
        comment="Overview of what the document is and why it is required for welfare schemes",
    )
    issuing_department = Column(
        String(255),
        nullable=False,
        comment="Central/State issuing department name",
    )
    state_specific_authority = Column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="State-wise issuing authority map (e.g. Maharashtra: Tahsildar/Aaple Sarkar, Gujarat: Mamlatdar/Digital Gujarat)",
    )
    required_supporting_documents = Column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
        comment="List of supporting proofs needed to obtain this document",
    )
    online_steps = Column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Multilingual step-by-step instructions for online portal application {'en': [...], 'hi': [...], 'gu': [...]}",
    )
    offline_steps = Column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Multilingual step-by-step instructions for offline physical submission {'en': [...], 'hi': [...], 'gu': [...]}",
    )
    fees_and_timelines = Column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Statutory government fees and SLA processing days under Public Services Act",
    )
    official_links = Column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Verified official portal URLs {'application_portal': '...', 'department_portal': '...', 'tracking_portal': '...'}",
    )
    languages_supported = Column(
        JSONB,
        nullable=False,
        default=list,
        server_default='["en", "hi", "gu"]',
        comment="List of supported translation languages",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SchemeAnalyticsDataset(Base):
    """Official government beneficiary dataset for a specific welfare scheme.
    
    Contains aggregate metrics strictly from verified government reports/dashboards.
    Never mixed with JanMitra platform applicant counts.
    """
    __tablename__ = "scheme_analytics_datasets"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary UUID key for analytics dataset",
    )
    scheme_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schemes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key referencing parent scheme",
    )
    source_name = Column(
        String(255),
        nullable=False,
        comment="Official government source name (e.g. Ministry Dashboard, Lok Sabha Standing Committee Report)",
    )
    report_title = Column(
        String(255),
        nullable=True,
        comment="Official report or publication document title",
    )
    source_url = Column(
        String(500),
        nullable=False,
        comment="Verified official portal or report URL",
    )
    source_publication_date = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date when the official source published this dataset",
    )
    reporting_period = Column(
        String(100),
        nullable=False,
        comment="Reporting period (e.g. 'FY 2024-25', 'Cumulative as of Dec 2025')",
    )
    geographic_scope = Column(
        String(100),
        nullable=False,
        default="National",
        server_default="National",
        comment="Geographic scope: National, State: Maharashtra, State: Gujarat, etc.",
    )
    metric_type = Column(
        String(100),
        nullable=False,
        default="unique_beneficiaries",
        comment="Metric definition: 'unique_beneficiaries', 'households', 'sanctioned_applications', etc.",
    )
    metric_definition = Column(
        Text,
        nullable=True,
        comment="Exact operational definition of metric e.g. cumulative verified farmers, sanctioned houses",
    )
    total_beneficiaries = Column(
        BigInteger,
        nullable=False,
        default=0,
        comment="Total verified aggregate beneficiary count",
    )
    dataset_version = Column(
        Integer,
        default=1,
        nullable=False,
        comment="Monotonically increasing version number for dataset history",
    )
    verification_status = Column(
        String(50),
        nullable=False,
        default="Pending Verification",
        index=True,
        comment="Freshness status: 'Verified', 'Pending Verification', 'Review Required', 'Stale', 'Unavailable'",
    )
    is_published = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Whether dataset is approved and published for citizen visibility",
    )
    published_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when dataset was published",
    )
    last_verified_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when administrative source verification was completed",
    )
    notes = Column(
        Text,
        nullable=True,
        comment="Methodology notes, exclusions, or government caveats",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    scheme = relationship("Scheme", backref="analytics_datasets")
    breakdowns = relationship("SchemeAnalyticsBreakdown", back_populates="dataset", cascade="all, delete-orphan")


class SchemeAnalyticsBreakdown(Base):
    """Categorical breakdown entry for an analytics dataset.
    
    Represents caste/category, geographic, gender, or yearly distribution.
    """
    __tablename__ = "scheme_analytics_breakdowns"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    dataset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scheme_analytics_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dimension = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Dimension: 'caste_category', 'state', 'district', 'gender', 'yearly_trend'",
    )
    category_name = Column(
        String(100),
        nullable=False,
        comment="Dimension slice label: 'SC', 'ST', 'OBC', 'General', 'EWS', 'Maharashtra', '2024', etc.",
    )
    metric_value = Column(
        BigInteger,
        nullable=False,
        default=0,
        comment="Metric count belonging to this slice",
    )
    percentage = Column(
        Float,
        nullable=True,
        comment="Proportion of total within same reporting period and metric (0-100%)",
    )
    notes = Column(
        String(255),
        nullable=True,
        comment="Source-specific footnote or classification remark",
    )

    dataset = relationship("SchemeAnalyticsDataset", back_populates="breakdowns")


class SchemeAnalyticsAuditLog(Base):
    """Audit ledger for administrative analytics imports and lifecycle changes."""
    __tablename__ = "scheme_analytics_audit_logs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    dataset_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    scheme_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    admin_id = Column(
        UUID(as_uuid=True),
        nullable=True,
    )
    action = Column(
        String(50),
        nullable=False,
        comment="Action: 'imported', 'validated', 'approved', 'published', 'unpublished', 'updated'",
    )
    details = Column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

