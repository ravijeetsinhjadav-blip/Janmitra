import uuid
from sqlalchemy import Column, String, Date, Numeric, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class UserProfile(Base):
    """Citizen demographic and socioeconomic profile for scheme eligibility assessment.
    
    Privacy rule: Aadhaar is deliberately excluded from general profile storage.
    """
    __tablename__ = "user_profiles"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary UUID key for citizen profile",
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        comment="Associated User account ID",
    )
    full_name = Column(
        String(150),
        nullable=False,
        comment="Citizen's legal full name",
    )
    date_of_birth = Column(
        Date,
        nullable=False,
        comment="Date of birth for age-based scheme criteria",
    )
    state = Column(
        String(100),
        nullable=False,
        index=True,
        comment="State / UT of residence for state-specific scheme eligibility",
    )
    district = Column(
        String(100),
        nullable=False,
        index=True,
        comment="District of residence",
    )
    residence_type = Column(
        String(20),
        nullable=False,
        default="rural",
        comment="Residence type: rural or urban",
    )
    annual_family_income = Column(
        Numeric(12, 2),
        nullable=True,
        comment="Annual family income in INR for income-threshold schemes",
    )
    occupation = Column(
        String(100),
        nullable=True,
        comment="Citizen occupation (e.g., Farmer, Student, Artisan, Self-Employed)",
    )
    education_level = Column(
        String(100),
        nullable=True,
        comment="Highest education level completed",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Profile creation timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Profile last updated timestamp",
    )

    # Relationships
    user = relationship("User", back_populates="profile")

    def __repr__(self) -> str:
        return f"<UserProfile id={self.id} user_id={self.user_id} name={self.full_name}>"
