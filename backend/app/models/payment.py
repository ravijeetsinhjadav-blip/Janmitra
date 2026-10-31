import uuid
from sqlalchemy import Column, String, Numeric, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base

PAYMENT_STATUSES = ["created", "captured", "failed", "refunded"]
PAYMENT_METHODS = ["upi", "card", "qr", "netbanking", "other"]


class PaymentTransaction(Base):
    """Payment transaction entity tracking Razorpay orders, payments, and webhooks."""
    __tablename__ = "payment_transactions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary UUID key for payment transaction",
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated citizen User ID",
    )
    subscription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated Subscription record if activated/renewed",
    )
    razorpay_order_id = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique Razorpay order ID (e.g. order_xxx)",
    )
    razorpay_payment_id = Column(
        String(100),
        nullable=True,
        unique=True,
        index=True,
        comment="Unique Razorpay payment ID (e.g. pay_xxx)",
    )
    razorpay_signature = Column(
        String(255),
        nullable=True,
        comment="Cryptographic HMAC-SHA256 signature returned by Razorpay",
    )
    amount = Column(
        Numeric(10, 2),
        nullable=False,
        comment="Payment amount in INR (e.g. 99.00 or 799.00)",
    )
    currency = Column(
        String(10),
        nullable=False,
        default="INR",
        comment="Payment currency",
    )
    plan_type = Column(
        String(20),
        nullable=False,
        default="premium",
        comment="Subscription plan purchased: 'premium'",
    )
    billing_cycle = Column(
        String(20),
        nullable=False,
        comment="Billing cycle: 'monthly' or 'yearly'",
    )
    payment_status = Column(
        String(30),
        nullable=False,
        default="created",
        index=True,
        comment="Transaction status: created, captured, failed, refunded",
    )
    payment_method = Column(
        String(50),
        nullable=True,
        comment="Payment instrument: upi, card, qr, netbanking",
    )
    error_code = Column(
        String(100),
        nullable=True,
        comment="Error code if payment failed",
    )
    error_description = Column(
        Text,
        nullable=True,
        comment="Detailed failure reason returned by Razorpay",
    )
    idempotency_key = Column(
        String(100),
        nullable=True,
        unique=True,
        index=True,
        comment="Idempotency key to prevent duplicate processing",
    )
    payment_metadata = Column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Raw verified webhook payloads and audit telemetry",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Transaction creation timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Transaction last modified timestamp",
    )

    # Relationships
    user = relationship("User", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payments")

    def __repr__(self) -> str:
        return f"<PaymentTransaction id={self.id} order={self.razorpay_order_id} status='{self.payment_status}'>"
