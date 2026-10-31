import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

# Approved subscription plans and pricing:
# Free: Basic eligibility checks
# Premium: Unlimited checks, advanced document verification guidance, priority readiness reports
# - Monthly:    ₹99 / month
# - Yearly:     ₹799 / year
PLAN_TYPES = ["free", "premium"]
BILLING_CYCLES = ["monthly", "yearly"]


class Subscription(Base):
    """User subscription status tracking entity.
    
    Architecture Note:
    In Phase 2, this model defines the subscription schema.
    Actual payment gateway transactions (Razorpay) and quota restrictions
    are implemented in subsequent phases.
    """
    __tablename__ = "subscriptions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary UUID key for subscription record",
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Subscriber user ID",
    )
    plan_type = Column(
        String(20),
        nullable=False,
        default="free",
        index=True,
        comment="Subscription tier: 'free' or 'premium'",
    )
    billing_cycle = Column(
        String(20),
        nullable=True,
        comment="Billing frequency: 'monthly' or 'yearly'",
    )
    status = Column(
        String(20),
        nullable=False,
        default="active",
        index=True,
        comment="Status: 'active', 'expired', 'cancelled', 'pending'",
    )
    start_date = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Subscription start timestamp",
    )
    end_date = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Subscription expiry timestamp (null for permanent free tier)",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Record last updated timestamp",
    )

    # Relationships
    user = relationship("User", back_populates="subscriptions")
    payments = relationship("PaymentTransaction", back_populates="subscription")

    def __repr__(self) -> str:
        return f"<Subscription id={self.id} user_id={self.user_id} plan='{self.plan_type}' status='{self.status}'>"


class UserMonthlyQuota(Base):
    """Tracks atomic consumption of monthly quota allocations per citizen."""
    __tablename__ = "user_monthly_quotas"
    __table_args__ = (
        UniqueConstraint("user_id", "year_month", name="uq_user_monthly_quota"),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary UUID key for monthly quota record",
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated citizen user ID",
    )
    year_month = Column(
        String(7),
        nullable=False,
        index=True,
        comment="Calendar month formatted as YYYY-MM (e.g. 2026-10)",
    )
    guidance_sessions_used = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Count of consumed AI guidance sessions this calendar month",
    )
    doc_analyses_used = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Count of consumed AI document analyses this calendar month",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Quota ledger record creation timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Quota ledger record last updated timestamp",
    )

    user = relationship("User")

    def __repr__(self) -> str:
        return f"<UserMonthlyQuota user_id={self.user_id} ym='{self.year_month}' guidance={self.guidance_sessions_used} docs={self.doc_analyses_used}>"


