import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

# Approved subscription plans and pricing:
# Free: Basic eligibility checks
# Premium: Unlimited checks, advanced document verification guidance, priority readiness reports
# - Monthly:    ₹99 / month
# - 6 Months:   ₹499 / 6 months
# - Yearly:     ₹899 / year
PLAN_TYPES = ["free", "premium"]
BILLING_CYCLES = ["monthly", "six_months", "yearly"]


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
        comment="Billing frequency: 'monthly', 'six_months', or 'yearly'",
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

    def __repr__(self) -> str:
        return f"<Subscription id={self.id} user_id={self.user_id} plan='{self.plan_type}' status='{self.status}'>"

