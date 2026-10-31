import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models.subscription import Subscription, UserMonthlyQuota, PLAN_TYPES, BILLING_CYCLES
from app.models.document import DocumentMetadata, DocumentProcessingStatus
from app.models.assessment import Assessment
from app.schemas.subscription import (
    SubscriptionPlanItem,
    SubscriptionPlansResponse,
    UsageQuotaStatus,
    CitizenSubscriptionResponse,
)
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("janmitra.subscription_service")


def _normalize_dt(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime is offset-aware in UTC for safe comparisons across all database dialects."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class SubscriptionService:
    """Manages subscription tier definitions, citizen subscription lifecycle,
    and server-side monthly quota enforcement.
    """

    @classmethod
    def get_plans_catalog(cls) -> SubscriptionPlansResponse:
        """Return standardized platform subscription plans."""
        plans = [
            SubscriptionPlanItem(
                plan_type="free",
                name="JanMitra Free",
                description="Essential welfare scheme discovery and preliminary eligibility assessment.",
                price_monthly=0.0,
                price_yearly=0.0,
                currency="INR",
                features=[
                    "Basic government scheme search and filtering",
                    "Deterministic eligibility assessment & criteria match %",
                    "Official government portal links and instructions",
                    f"Up to {settings.FREE_MONTHLY_DOC_ANALYSES_LIMIT} AI document analyses per month",
                    f"Up to {settings.FREE_MONTHLY_AI_GUIDANCE_LIMIT} personalized AI guidance sessions per month",
                    "Basic document vault storage",
                ],
                doc_analyses_limit=settings.FREE_MONTHLY_DOC_ANALYSES_LIMIT,
                ai_guidance_limit=settings.FREE_MONTHLY_AI_GUIDANCE_LIMIT,
                is_popular=False,
            ),
            SubscriptionPlanItem(
                plan_type="premium",
                name="JanMitra Premium",
                description="Advanced application assistance, document consistency cross-checks, and expanded AI limits.",
                price_monthly=99.0,
                price_yearly=799.0,
                currency="INR",
                features=[
                    "Everything in Free Plan",
                    f"Up to {settings.PREMIUM_MONTHLY_DOC_ANALYSES_LIMIT} AI document analyses per month",
                    f"Expanded AI advisory guidance (fair-use safety ceiling: up to {settings.PREMIUM_MONTHLY_AI_GUIDANCE_LIMIT} sessions per month; subject to confirmation)",
                    "Advanced document consistency & identity cross-checks",
                    "Priority application assistance with interactive checklists",
                    "Common mistakes alerts (merged bank IFSCs, spelling mismatches)",
                    "Multilingual Devanagari Hindi and Gujarati guidance",
                    "Unlimited scheme discovery & recommendation matching",
                ],
                doc_analyses_limit=settings.PREMIUM_MONTHLY_DOC_ANALYSES_LIMIT,
                ai_guidance_limit=settings.PREMIUM_MONTHLY_AI_GUIDANCE_LIMIT,
                is_popular=True,
            ),
        ]
        return SubscriptionPlansResponse(plans=plans)

    @classmethod
    def get_active_subscription(cls, db: Session, user_id: uuid.UUID) -> Subscription:
        """Retrieve user's active subscription, automatically expiring past subscriptions."""
        now = datetime.now(timezone.utc)
        sub = (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
                Subscription.status == "active",
            )
            .order_by(Subscription.created_at.desc())
            .first()
        )

        if sub:
            # Check for expiry
            end_utc = _normalize_dt(sub.end_date)
            if end_utc and end_utc < now:
                logger.info(f"Subscription {sub.id} for user {user_id} expired on {sub.end_date}")
                sub.status = "expired"
                db.commit()
                db.refresh(sub)
                sub = None

        if not sub:
            # Default to free tier
            sub = (
                db.query(Subscription)
                .filter(
                    Subscription.user_id == user_id,
                    Subscription.plan_type == "free",
                )
                .first()
            )
            if not sub:
                sub = Subscription(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    plan_type="free",
                    billing_cycle=None,
                    status="active",
                    start_date=now,
                    end_date=None,
                )
                db.add(sub)
                db.commit()
                db.refresh(sub)

        return sub

    @classmethod
    def get_or_create_monthly_quota_record(
        cls, db: Session, user_id: uuid.UUID, for_update: bool = False
    ) -> Optional[UserMonthlyQuota]:
        """Retrieve or initialize the citizen's atomic monthly quota record."""
        now = datetime.now(timezone.utc)
        ym = f"{now.year:04d}-{now.month:02d}"

        query = db.query(UserMonthlyQuota).filter(
            UserMonthlyQuota.user_id == user_id,
            UserMonthlyQuota.year_month == ym,
        )
        if for_update:
            query = query.with_for_update()

        record = query.first()
        if not record:
            month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
            doc_count = (
                db.query(func.count(DocumentMetadata.id))
                .filter(
                    DocumentMetadata.user_id == user_id,
                    DocumentMetadata.ocr_status.in_([
                        DocumentProcessingStatus.OCR_COMPLETED,
                        DocumentProcessingStatus.MANUAL_REVIEW_REQUIRED,
                    ]),
                    DocumentMetadata.created_at >= month_start,
                )
                .scalar()
                or 0
            )
            guidance_count = (
                db.query(func.count(Assessment.id))
                .filter(
                    Assessment.user_id == user_id,
                    Assessment.advisory_guidance != {},
                    Assessment.created_at >= month_start,
                )
                .scalar()
                or 0
            )
            try:
                record = UserMonthlyQuota(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    year_month=ym,
                    guidance_sessions_used=guidance_count,
                    doc_analyses_used=doc_count,
                )
                db.add(record)
                db.commit()
                db.refresh(record)
            except Exception:
                db.rollback()
                query = db.query(UserMonthlyQuota).filter(
                    UserMonthlyQuota.user_id == user_id,
                    UserMonthlyQuota.year_month == ym,
                )
                if for_update:
                    query = query.with_for_update()
                record = query.first()
        return record

    @classmethod
    def auto_heal_stale_processing_documents(
        cls, db: Session, user_id: uuid.UUID, stale_seconds: int = 300
    ) -> int:
        """Auto-heal abandoned in-flight reservations (SEC-05).
        
        Any DocumentMetadata record for this user remaining in PROCESSING or PENDING_OCR status
        longer than stale_seconds (default 5 minutes) represents a crashed, killed, or abandoned
        worker. It is transitioned to OCR_FAILED so the citizen's quota is never stuck indefinitely.
        """
        threshold = datetime.now(timezone.utc) - timedelta(seconds=stale_seconds)
        stale_docs = (
            db.query(DocumentMetadata)
            .filter(
                DocumentMetadata.user_id == user_id,
                DocumentMetadata.ocr_status.in_([
                    DocumentProcessingStatus.PROCESSING,
                    DocumentProcessingStatus.PENDING_OCR,
                ]),
                DocumentMetadata.created_at < threshold,
            )
            .all()
        )
        if stale_docs:
            for d in stale_docs:
                d.ocr_status = DocumentProcessingStatus.OCR_FAILED
                d.ocr_error_message = "OCR processing timed out or server restarted"
                d.manual_review_required = True
            db.commit()
            logger.info(f"Auto-healed {len(stale_docs)} stale processing documents for user {user_id}")
        return len(stale_docs)

    @classmethod
    def get_quota_status(cls, db: Session, user_id: uuid.UUID) -> UsageQuotaStatus:
        """Calculate current calendar month usage against plan quota limits.
        SEC-05: Exclude OCR_FAILED documents so citizens are not penalized for failed extractions.
        SEC-06: Backed by atomic monthly quota ledger with in-flight reservation safety.
        """
        now = datetime.now(timezone.utc)
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        # Next month reset date
        if now.month == 12:
            reset_date = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            reset_date = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)

        sub = cls.get_active_subscription(db, user_id)
        is_premium = sub.plan_type == "premium" and sub.status == "active"

        doc_limit = (
            settings.PREMIUM_MONTHLY_DOC_ANALYSES_LIMIT
            if is_premium
            else settings.FREE_MONTHLY_DOC_ANALYSES_LIMIT
        )
        guidance_limit = (
            settings.PREMIUM_MONTHLY_AI_GUIDANCE_LIMIT
            if is_premium
            else settings.FREE_MONTHLY_AI_GUIDANCE_LIMIT
        )

        # 1. Auto-heal any stale processing records older than 5 minutes
        cls.auto_heal_stale_processing_documents(db, user_id)

        quota_record = cls.get_or_create_monthly_quota_record(db, user_id, for_update=False)

        # 2. Count usable document analyses this month (SEC-05: only completed / manual review)
        live_doc_count = (
            db.query(func.count(DocumentMetadata.id))
            .filter(
                DocumentMetadata.user_id == user_id,
                DocumentMetadata.ocr_status.in_([
                    DocumentProcessingStatus.OCR_COMPLETED,
                    DocumentProcessingStatus.MANUAL_REVIEW_REQUIRED,
                ]),
                DocumentMetadata.created_at >= month_start,
            )
            .scalar()
            or 0
        )

        # 3. Count active in-flight processing documents (reserved slots)
        in_flight_count = (
            db.query(func.count(DocumentMetadata.id))
            .filter(
                DocumentMetadata.user_id == user_id,
                DocumentMetadata.ocr_status.in_([
                    DocumentProcessingStatus.PROCESSING,
                    DocumentProcessingStatus.PENDING_OCR,
                ]),
                DocumentMetadata.created_at >= month_start,
            )
            .scalar()
            or 0
        )

        # 4. Count AI guidance sessions this month
        live_guidance_count = (
            db.query(func.count(Assessment.id))
            .filter(
                Assessment.user_id == user_id,
                Assessment.advisory_guidance != {},
                Assessment.created_at >= month_start,
            )
            .scalar()
            or 0
        )

        # Reconcile ledger doc_analyses_used if out of sync with actual completed docs
        if quota_record and quota_record.doc_analyses_used != live_doc_count:
            try:
                quota_record.doc_analyses_used = live_doc_count
                db.commit()
            except Exception:
                db.rollback()

        doc_count = live_doc_count
        guidance_count = max(quota_record.guidance_sessions_used if quota_record else 0, live_guidance_count)

        can_analyze = (doc_count + in_flight_count) < doc_limit
        can_guide = guidance_count < guidance_limit

        return UsageQuotaStatus(
            ai_document_analyses_used=doc_count,
            ai_document_analyses_limit=doc_limit,
            ai_guidance_sessions_used=guidance_count,
            ai_guidance_sessions_limit=guidance_limit,
            can_analyze_document=can_analyze,
            can_request_guidance=can_guide,
            quota_reset_date=reset_date,
        )

    @classmethod
    def reserve_and_consume_guidance_quota(cls, db: Session, user_id: uuid.UUID) -> None:
        """Atomically verify and consume 1 AI guidance session under row-level lock (SEC-06)."""
        cls.enforce_ai_guidance_quota(db, user_id)
        quota_record = cls.get_or_create_monthly_quota_record(db, user_id, for_update=True)
        if quota_record:
            quota_record.guidance_sessions_used += 1
            db.commit()
            db.refresh(quota_record)

    @classmethod
    def release_guidance_quota(cls, db: Session, user_id: uuid.UUID) -> None:
        """Release 1 previously reserved AI guidance session if LLM execution failed (SEC-06)."""
        quota_record = cls.get_or_create_monthly_quota_record(db, user_id, for_update=True)
        if quota_record and quota_record.guidance_sessions_used > 0:
            quota_record.guidance_sessions_used -= 1
            db.commit()

    @classmethod
    def reserve_document_analysis_quota(cls, db: Session, user_id: uuid.UUID) -> None:
        """Atomically verify and reserve 1 document analysis quota unit under row lock (SEC-05, SEC-06).
        
        Serializes concurrent uploads and prevents TOCTOU race conditions.
        Counts both completed documents and active in-flight PROCESSING documents.
        """
        now = datetime.now(timezone.utc)
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

        # 1. Acquire row-level pessimistic lock on the user's monthly quota record
        quota_record = cls.get_or_create_monthly_quota_record(db, user_id, for_update=True)

        # 2. Auto-heal any stale processing documents
        cls.auto_heal_stale_processing_documents(db, user_id)

        # 3. Determine active subscription limit
        sub = cls.get_active_subscription(db, user_id)
        is_premium = sub.plan_type == "premium" and sub.status == "active"
        doc_limit = (
            settings.PREMIUM_MONTHLY_DOC_ANALYSES_LIMIT
            if is_premium
            else settings.FREE_MONTHLY_DOC_ANALYSES_LIMIT
        )

        # 4. Count completed and active in-flight processing documents
        completed_count = (
            db.query(func.count(DocumentMetadata.id))
            .filter(
                DocumentMetadata.user_id == user_id,
                DocumentMetadata.ocr_status.in_([
                    DocumentProcessingStatus.OCR_COMPLETED,
                    DocumentProcessingStatus.MANUAL_REVIEW_REQUIRED,
                ]),
                DocumentMetadata.created_at >= month_start,
            )
            .scalar()
            or 0
        )
        in_flight_count = (
            db.query(func.count(DocumentMetadata.id))
            .filter(
                DocumentMetadata.user_id == user_id,
                DocumentMetadata.ocr_status.in_([
                    DocumentProcessingStatus.PROCESSING,
                    DocumentProcessingStatus.PENDING_OCR,
                ]),
                DocumentMetadata.created_at >= month_start,
            )
            .scalar()
            or 0
        )

        total_in_use = completed_count + in_flight_count
        if total_in_use >= doc_limit:
            logger.warning(
                f"User {user_id} exceeded document analysis quota: "
                f"{total_in_use}/{doc_limit} (completed={completed_count}, in_flight={in_flight_count})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Monthly AI document analysis quota reached "
                    f"({completed_count}/{doc_limit}). "
                    f"Please upgrade to JanMitra Premium for up to "
                    f"{settings.PREMIUM_MONTHLY_DOC_ANALYSES_LIMIT} monthly document extractions."
                ),
            )

        # Synchronize ledger record
        if quota_record:
            quota_record.doc_analyses_used = completed_count
            db.commit()

    @classmethod
    def finalize_document_analysis(cls, db: Session, user_id: uuid.UUID) -> None:
        """Finalize quota consumption upon successful OCR extraction (SEC-05)."""
        now = datetime.now(timezone.utc)
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

        quota_record = cls.get_or_create_monthly_quota_record(db, user_id, for_update=True)
        completed_count = (
            db.query(func.count(DocumentMetadata.id))
            .filter(
                DocumentMetadata.user_id == user_id,
                DocumentMetadata.ocr_status.in_([
                    DocumentProcessingStatus.OCR_COMPLETED,
                    DocumentProcessingStatus.MANUAL_REVIEW_REQUIRED,
                ]),
                DocumentMetadata.created_at >= month_start,
            )
            .scalar()
            or 0
        )
        if quota_record:
            quota_record.doc_analyses_used = completed_count
            db.commit()
            db.refresh(quota_record)

    @classmethod
    def release_document_analysis_quota(cls, db: Session, user_id: uuid.UUID) -> None:
        """Release reservation if OCR extraction failed or document processing aborted (SEC-05)."""
        now = datetime.now(timezone.utc)
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

        quota_record = cls.get_or_create_monthly_quota_record(db, user_id, for_update=True)
        completed_count = (
            db.query(func.count(DocumentMetadata.id))
            .filter(
                DocumentMetadata.user_id == user_id,
                DocumentMetadata.ocr_status.in_([
                    DocumentProcessingStatus.OCR_COMPLETED,
                    DocumentProcessingStatus.MANUAL_REVIEW_REQUIRED,
                ]),
                DocumentMetadata.created_at >= month_start,
            )
            .scalar()
            or 0
        )
        if quota_record:
            quota_record.doc_analyses_used = completed_count
            db.commit()

    @classmethod
    def consume_document_analysis_quota(cls, db: Session, user_id: uuid.UUID) -> None:
        """Backward-compatible helper: reserves document quota under row lock (SEC-06)."""
        cls.reserve_document_analysis_quota(db, user_id)

    @classmethod
    def enforce_document_analysis_quota(cls, db: Session, user_id: uuid.UUID) -> None:
        """Raise 403 Forbidden if user has exceeded their monthly document analysis quota."""
        quota = cls.get_quota_status(db, user_id)
        if not quota.can_analyze_document:
            logger.warning(
                f"User {user_id} exceeded document analysis quota: "
                f"{quota.ai_document_analyses_used}/{quota.ai_document_analyses_limit}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Monthly AI document analysis quota reached "
                    f"({quota.ai_document_analyses_used}/{quota.ai_document_analyses_limit}). "
                    f"Please upgrade to JanMitra Premium for up to "
                    f"{settings.PREMIUM_MONTHLY_DOC_ANALYSES_LIMIT} monthly document extractions."
                ),
            )

    @classmethod
    def enforce_ai_guidance_quota(cls, db: Session, user_id: uuid.UUID) -> None:
        """Raise 403 Forbidden if user has exceeded their monthly AI guidance session quota."""
        quota = cls.get_quota_status(db, user_id)
        if not quota.can_request_guidance:
            logger.warning(
                f"User {user_id} exceeded AI guidance quota: "
                f"{quota.ai_guidance_sessions_used}/{quota.ai_guidance_sessions_limit}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Monthly personalized AI guidance quota reached "
                    f"({quota.ai_guidance_sessions_used}/{quota.ai_guidance_sessions_limit}). "
                    f"Please upgrade to JanMitra Premium for expanded AI advisory access."
                ),
            )

    @classmethod
    def get_citizen_subscription_response(
        cls, db: Session, user_id: uuid.UUID
    ) -> CitizenSubscriptionResponse:
        """Retrieve user's full subscription details with quota usage matching schema."""
        sub = cls.get_active_subscription(db, user_id)
        quota = cls.get_quota_status(db, user_id)

        # Days remaining for paid subscription
        days_remaining = None
        if sub.end_date:
            end_utc = _normalize_dt(sub.end_date)
            now_utc = datetime.now(timezone.utc)
            delta = end_utc - now_utc
            days_remaining = max(0, delta.days)

        return CitizenSubscriptionResponse(
            user_id=user_id,
            plan_type=sub.plan_type,
            billing_cycle=sub.billing_cycle,
            status=sub.status,
            is_active=(sub.status == "active"),
            start_date=sub.start_date,
            end_date=sub.end_date,
            days_remaining=days_remaining,
            usage=quota,
        )

    @classmethod
    def activate_premium_subscription(
        cls,
        db: Session,
        user_id: uuid.UUID,
        billing_cycle: str,
        transaction_id: Optional[uuid.UUID] = None,
    ) -> Subscription:
        """Activate or extend a citizen's Premium subscription."""
        now = datetime.now(timezone.utc)
        cycle = billing_cycle.lower()

        # Calculate duration
        if cycle == "yearly":
            duration = timedelta(days=365)
        elif cycle == "monthly":
            duration = timedelta(days=30)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid billing cycle '{billing_cycle}'. Expected 'monthly' or 'yearly'.",
            )

        # Check existing active subscription to extend or start new
        current_sub = (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
                Subscription.plan_type == "premium",
                Subscription.status == "active",
            )
            .with_for_update()
            .order_by(Subscription.end_date.desc())
            .first()
        )

        if current_sub and current_sub.end_date:
            current_end = _normalize_dt(current_sub.end_date)
            if current_end and current_end > now:
                new_start = current_sub.start_date
                new_end = current_end + duration
                current_sub.end_date = new_end
                current_sub.billing_cycle = cycle
                db.commit()
                db.refresh(current_sub)
                logger.info(
                    f"Extended existing premium subscription {current_sub.id} "
                    f"for user {user_id} until {new_end}"
                )
                return current_sub

        # Deactivate any previous active subscriptions
        db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == "active",
        ).update({"status": "superseded"})

        # Create new premium subscription
        new_sub = Subscription(
            id=uuid.uuid4(),
            user_id=user_id,
            plan_type="premium",
            billing_cycle=cycle,
            status="active",
            start_date=now,
            end_date=now + duration,
        )
        db.add(new_sub)
        db.commit()
        db.refresh(new_sub)
        logger.info(
            f"Activated new premium subscription {new_sub.id} for user {user_id} until {new_sub.end_date}"
        )
        return new_sub
