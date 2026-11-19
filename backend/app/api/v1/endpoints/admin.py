import uuid
import math
from datetime import datetime, timezone
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.models.user import User
from app.models.profile import UserProfile
from app.models.scheme import Scheme
from app.models.document import DocumentMetadata
from app.models.assessment import Assessment
from app.models.application import Application, APPLICATION_STATUSES
from app.models.subscription import Subscription
from app.models.payment import PaymentTransaction
from app.schemas.admin import (
    AdminStatsResponse,
    AdminUserListResponse,
    AdminUserListItem,
    AdminUserDetailResponse,
    AdminUserStatusUpdate,
    AdminSchemeCreate,
    AdminSchemeUpdate,
    AdminApplicationListResponse,
    AdminApplicationListItem,
    AdminSubscriptionListResponse,
    AdminSubscriptionListItem,
    AdminPaymentListResponse,
    AdminPaymentListItem,
)

router = APIRouter()


@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get overall administrative platform metrics",
    description="Returns high-level statistics across users, schemes, applications, documents, and payments.",
)
def get_admin_stats(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    total_citizens = db.query(User).filter(User.role == "citizen").count()
    active_citizens = db.query(User).filter(User.role == "citizen", User.is_active == True).count()

    total_schemes = db.query(Scheme).count()
    active_schemes = db.query(Scheme).filter(Scheme.is_active == True).count()

    total_applications = db.query(Application).count()

    # Application status breakdown
    status_counts = db.query(Application.status, func.count(Application.id)).group_by(Application.status).all()
    status_map = {s: 0 for s in APPLICATION_STATUSES}
    for st, count in status_counts:
        status_map[st] = count

    total_documents = db.query(DocumentMetadata).count()
    ocr_completed = db.query(DocumentMetadata).filter(DocumentMetadata.ocr_status == "OCR_COMPLETED").count()
    manual_review = db.query(DocumentMetadata).filter(DocumentMetadata.manual_review_required == True).count()

    total_assessments = db.query(Assessment).count()
    active_premium = db.query(Subscription).filter(
        Subscription.plan_type == "premium",
        Subscription.status == "active",
    ).count()

    captured_payments = db.query(PaymentTransaction).filter(
        PaymentTransaction.payment_status == "captured",
    ).count()

    active_subscriptions = db.query(Subscription).filter(Subscription.status == "active").count()
    expired_subscriptions = db.query(Subscription).filter(Subscription.status == "expired").count()
    cancelled_subscriptions = db.query(Subscription).filter(Subscription.status == "cancelled").count()
    total_premium_users = active_premium
    total_free_users = max(0, total_citizens - total_premium_users)

    revenue_result = db.query(
        func.sum(
            PaymentTransaction.amount
            - func.coalesce(PaymentTransaction.amount_refunded, 0.0)
        )
    ).filter(
        PaymentTransaction.payment_status.in_(["captured", "partially_refunded"])
    ).scalar()
    total_revenue_inr = max(0.0, round(float(revenue_result or 0.0), 2))

    return AdminStatsResponse(
        total_citizens=total_citizens,
        active_citizens=active_citizens,
        total_schemes=total_schemes,
        active_schemes=active_schemes,
        total_applications=total_applications,
        applications_by_status=status_map,
        total_documents=total_documents,
        ocr_completed_documents=ocr_completed,
        manual_review_documents=manual_review,
        total_assessments=total_assessments,
        total_active_premium_subscriptions=active_premium,
        total_payments_captured=captured_payments,
        total_free_users=total_free_users,
        total_premium_users=total_premium_users,
        active_subscriptions=active_subscriptions,
        expired_subscriptions=expired_subscriptions,
        cancelled_subscriptions=cancelled_subscriptions,
        total_revenue_inr=total_revenue_inr,
        system_status="operational",
    )


@router.get(
    "/users",
    response_model=AdminUserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List registered citizen accounts",
    description="Retrieve paginated list of citizens with optional search by mobile or name.",
)
def list_admin_users(
    query: Optional[str] = Query(None, description="Search query by mobile number or name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = db.query(User).outerjoin(UserProfile, User.id == UserProfile.user_id).filter(User.role == "citizen")

    if is_active is not None:
        q = q.filter(User.is_active == is_active)

    if query and query.strip():
        term = f"%{query.strip().lower()}%"
        q = q.filter(
            or_(
                User.email.ilike(term),
                User.mobile_number.ilike(term),
                UserProfile.full_name.ilike(term),
                UserProfile.state.ilike(term),
            )
        )

    total = q.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size
    users = q.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()

    items = []
    for u in users:
        items.append(
            AdminUserListItem(
                id=u.id,
                mobile_number=u.mobile_number,
                email=u.email,
                role=u.role,
                is_active=u.is_active,
                full_name=u.profile.full_name if u.profile else None,
                state=u.profile.state if u.profile else None,
                district=u.profile.district if u.profile else None,
                created_at=u.created_at,
            )
        )

    return AdminUserListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        users=items,
    )


@router.get(
    "/users/{user_id}",
    response_model=AdminUserDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get citizen account inspection details",
)
def get_admin_user_detail(
    user_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id, User.role == "citizen").first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Citizen account not found")

    docs_count = db.query(DocumentMetadata).filter(DocumentMetadata.user_id == user.id).count()
    apps_count = db.query(Application).filter(Application.user_id == user.id).count()

    sub = db.query(Subscription).filter(
        Subscription.user_id == user.id,
        Subscription.status == "active",
    ).first()

    prof_data = None
    if user.profile:
        p = user.profile
        prof_data = {
            "full_name": p.full_name,
            "date_of_birth": p.date_of_birth.isoformat() if p.date_of_birth else None,
            "state": p.state,
            "district": p.district,
            "residence_type": p.residence_type,
            "annual_family_income": float(p.annual_family_income) if p.annual_family_income else None,
            "occupation": p.occupation,
            "education_level": p.education_level,
        }

    return AdminUserDetailResponse(
        id=user.id,
        mobile_number=user.mobile_number,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        profile=prof_data,
        documents_count=docs_count,
        applications_count=apps_count,
        subscription_plan=sub.plan_type if sub else "free",
        subscription_active=bool(sub),
    )


@router.patch(
    "/users/{user_id}/status",
    status_code=status.HTTP_200_OK,
    summary="Update citizen account active status (activate/deactivate)",
)
def update_user_status(
    user_id: uuid.UUID,
    payload: AdminUserStatusUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id, User.role == "citizen").first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Citizen account not found")

    user.is_active = payload.is_active
    db.commit()
    return {
        "status": "success",
        "user_id": str(user.id),
        "is_active": user.is_active,
        "message": f"User account has been {'activated' if user.is_active else 'deactivated'}.",
    }


@router.get(
    "/schemes",
    status_code=status.HTTP_200_OK,
    summary="List schemes for administrative management",
)
def list_admin_schemes(
    query: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = db.query(Scheme)
    if is_active is not None:
        q = q.filter(Scheme.is_active == is_active)
    if category and category.strip():
        q = q.filter(Scheme.category == category.strip())
    if query and query.strip():
        term = f"%{query.strip().lower()}%"
        q = q.filter(or_(Scheme.scheme_name.ilike(term), Scheme.department.ilike(term)))

    total = q.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size
    schemes = q.order_by(Scheme.scheme_name.asc()).offset(offset).limit(page_size).all()

    items = []
    for s in schemes:
        items.append({
            "id": str(s.id),
            "scheme_name": s.scheme_name,
            "category": s.category,
            "department": s.department,
            "description": s.description,
            "short_description": s.short_description,
            "state_applicability": s.state_applicability,
            "official_source_url": s.official_source_url,
            "official_application_url": s.official_application_url,
            "source_freshness_status": s.source_freshness_status,
            "is_active": s.is_active,
            "is_demo_data": s.is_demo_data,
            "benefits": s.benefits,
            "eligibility_criteria": s.eligibility_criteria,
            "required_documents": s.required_documents,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "schemes": items,
    }


@router.post(
    "/schemes",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new government scheme record",
)
def create_admin_scheme(
    payload: AdminSchemeCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    scheme = Scheme(
        id=uuid.uuid4(),
        scheme_name=payload.scheme_name,
        category=payload.category,
        department=payload.department,
        description=payload.description,
        short_description=payload.short_description or payload.description[:200],
        state_applicability=payload.state_applicability,
        eligibility_summary=payload.eligibility_summary,
        official_source_url=payload.official_source_url,
        official_application_url=payload.official_application_url,
        benefits=payload.benefits,
        eligibility_criteria=payload.eligibility_criteria,
        required_profile_fields=payload.required_profile_fields,
        required_documents=payload.required_documents,
        application_process=payload.application_process,
        source_verification_details=payload.source_verification_details,
        source_freshness_status="Verified Official Source" if not payload.is_demo_data else "Pending Verification",
        is_demo_data=payload.is_demo_data,
        is_active=True,
    )
    db.add(scheme)
    db.commit()
    db.refresh(scheme)
    return {
        "status": "success",
        "id": str(scheme.id),
        "scheme_name": scheme.scheme_name,
        "message": "Scheme created successfully.",
    }


@router.patch(
    "/schemes/{scheme_id}",
    status_code=status.HTTP_200_OK,
    summary="Update scheme details, verification status, or activate/deactivate",
)
def update_admin_scheme(
    scheme_id: uuid.UUID,
    payload: AdminSchemeUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheme not found")

    update_dict = payload.model_dump(exclude_unset=True)
    for key, val in update_dict.items():
        if hasattr(scheme, key):
            setattr(scheme, key, val)

    db.commit()
    db.refresh(scheme)
    return {
        "status": "success",
        "id": str(scheme.id),
        "scheme_name": scheme.scheme_name,
        "is_active": scheme.is_active,
        "source_freshness_status": scheme.source_freshness_status,
        "message": "Scheme updated successfully.",
    }


@router.get(
    "/applications",
    response_model=AdminApplicationListResponse,
    status_code=status.HTTP_200_OK,
    summary="Monitor citizen application tracking activity",
    description="Provides administrative oversight of citizen-reported application statuses without claiming official government approval authority.",
)
def monitor_applications(
    status_filter: Optional[str] = Query(None, alias="status"),
    scheme_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = db.query(Application).join(Scheme, Application.scheme_id == Scheme.id)

    if status_filter and status_filter.strip() and status_filter != "All":
        q = q.filter(Application.status == status_filter.strip())
    if scheme_id:
        q = q.filter(Application.scheme_id == scheme_id)

    total = q.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size
    apps = q.order_by(Application.created_at.desc()).offset(offset).limit(page_size).all()

    # Status summary breakdown across all applications
    counts = db.query(Application.status, func.count(Application.id)).group_by(Application.status).all()
    summary = {s: 0 for s in APPLICATION_STATUSES}
    for st, cnt in counts:
        summary[st] = cnt

    items = []
    for a in apps:
        items.append(
            AdminApplicationListItem(
                id=a.id,
                user_id=a.user_id,
                scheme_id=a.scheme_id,
                scheme_name=a.scheme.scheme_name if a.scheme else "Unknown Scheme",
                category=a.scheme.category if a.scheme else None,
                status=a.status,
                application_reference_number=a.application_reference_number,
                submission_date=a.submission_date,
                created_at=a.created_at,
                updated_at=a.updated_at,
                source_qualification="Citizen Reported",
            )
        )

    return AdminApplicationListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        applications=items,
        status_summary=summary,
    )


@router.get(
    "/subscriptions",
    response_model=AdminSubscriptionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all citizen subscriptions with status and filtering",
)
def list_admin_subscriptions(
    plan_type: Optional[str] = Query(None, description="Filter by plan: free or premium"),
    status: Optional[str] = Query(None, description="Filter by status: active, expired, cancelled"),
    query: Optional[str] = Query(None, description="Search query by mobile number or citizen name"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Retrieve paginated citizen subscriptions for administrative oversight."""
    q = db.query(Subscription, User, UserProfile).join(
        User, Subscription.user_id == User.id
    ).outerjoin(
        UserProfile, User.id == UserProfile.user_id
    )

    if plan_type:
        q = q.filter(Subscription.plan_type == plan_type.lower())
    if status:
        q = q.filter(Subscription.status == status.lower())
    if query:
        search_pattern = f"%{query}%"
        q = q.filter(
            or_(
                User.email.ilike(search_pattern),
                User.mobile_number.ilike(search_pattern),
                UserProfile.full_name.ilike(search_pattern),
            )
        )

    total = q.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    results = q.order_by(Subscription.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    now = datetime.now(timezone.utc)
    items = []
    for sub, user, prof in results:
        days_rem = None
        if sub.end_date:
            end_utc = sub.end_date if sub.end_date.tzinfo else sub.end_date.replace(tzinfo=timezone.utc)
            delta = end_utc - now
            days_rem = max(0, delta.days)
        items.append(
            AdminSubscriptionListItem(
                id=sub.id,
                user_id=sub.user_id,
                citizen_name=prof.full_name if prof else "Unregistered Profile",
                mobile_number=user.mobile_number,
                plan_type=sub.plan_type,
                billing_cycle=sub.billing_cycle,
                status=sub.status,
                start_date=sub.start_date,
                end_date=sub.end_date,
                days_remaining=days_rem,
                created_at=sub.created_at,
            )
        )

    return AdminSubscriptionListResponse(
        total=total,
        items=items,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/payments",
    response_model=AdminPaymentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all payment transactions with audit metadata",
)
def list_admin_payments(
    status: Optional[str] = Query(None, description="Filter by status: created, captured, failed, refunded"),
    query: Optional[str] = Query(None, description="Search by order ID or payment ID or citizen mobile"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Retrieve paginated payment transactions for administrative revenue tracking."""
    q = db.query(PaymentTransaction, User, UserProfile).join(
        User, PaymentTransaction.user_id == User.id
    ).outerjoin(
        UserProfile, User.id == UserProfile.user_id
    )

    if status:
        q = q.filter(PaymentTransaction.payment_status == status.lower())
    if query:
        pattern = f"%{query}%"
        q = q.filter(
            or_(
                PaymentTransaction.razorpay_order_id.ilike(pattern),
                PaymentTransaction.razorpay_payment_id.ilike(pattern),
                User.email.ilike(pattern),
                User.mobile_number.ilike(pattern),
                UserProfile.full_name.ilike(pattern),
            )
        )

    total = q.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    results = q.order_by(PaymentTransaction.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for tx, user, prof in results:
        items.append(
            AdminPaymentListItem(
                id=tx.id,
                user_id=tx.user_id,
                citizen_name=prof.full_name if prof else "Unregistered Profile",
                mobile_number=user.mobile_number,
                razorpay_order_id=tx.razorpay_order_id,
                razorpay_payment_id=tx.razorpay_payment_id,
                amount=float(tx.amount),
                currency=tx.currency,
                plan_type=tx.plan_type,
                billing_cycle=tx.billing_cycle,
                payment_status=tx.payment_status,
                payment_method=tx.payment_method,
                error_description=tx.error_description,
                created_at=tx.created_at,
            )
        )

    return AdminPaymentListResponse(
        total=total,
        items=items,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "/reminders/process-due",
    status_code=status.HTTP_200_OK,
    summary="Trigger automated processing of due application reminders",
    description="Scans active citizen reminders due on or before current timestamp and dispatches push and in-app alerts.",
)
def trigger_process_due_reminders(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    from app.services.reminder_scheduler import ReminderSchedulerService
    return ReminderSchedulerService.process_due_reminders(db)
