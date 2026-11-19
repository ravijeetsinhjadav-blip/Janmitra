import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.core.dependencies import get_current_admin, get_current_user
from app.models.user import User
from app.models.scheme import Scheme
from app.models.scheme_intelligence import (
    SchemeCategoryRule,
    SchemeCategoryDocument,
    DocumentGuide,
    SchemeAnalyticsDataset,
    SchemeAnalyticsBreakdown,
    SchemeAnalyticsAuditLog,
)
from app.schemas.scheme_intelligence import (
    SchemeCategoryRuleBase,
    SchemeCategoryRuleResponse,
    SchemeCategoryRuleCreate,
    SchemeCategoryDocumentBase,
    SchemeCategoryDocumentResponse,
    SchemeCategoryDocumentCreate,
    CategoryRuleEvaluationRequest,
    CategoryRuleEvaluationResponse,
    CategoryRuleEvaluationItem,
    DocumentGuideBase,
    DocumentGuideResponse,
    DocumentGuideSummaryResponse,
    DocumentGuideCreate,
    SchemeAnalyticsDatasetBase,
    SchemeAnalyticsDatasetResponse,
    SchemeAnalyticsBreakdownBase,
    SchemeAnalyticsBreakdownResponse,
    SchemeAnalyticsImportRequest,
    SchemeAnalyticsAuditLogResponse,
)

# Citizen-facing router
router = APIRouter()

# Admin-facing router
admin_router = APIRouter()


# ============================================================================
# CITIZEN ENDPOINTS
# ============================================================================

@router.get(
    "/schemes/{scheme_id}/categories",
    response_model=List[str],
    summary="Get available categories for a scheme",
    description="Returns list of unique category options (e.g. General, OBC, SC, ST, EWS) available for this scheme.",
)
def get_scheme_available_categories(
    scheme_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    rule_cats = db.query(SchemeCategoryRule.category).filter(
        SchemeCategoryRule.scheme_id == scheme_id
    ).distinct().all()

    doc_cats = db.query(SchemeCategoryDocument.category).filter(
        SchemeCategoryDocument.scheme_id == scheme_id
    ).distinct().all()

    categories = set([r[0] for r in rule_cats] + [d[0] for d in doc_cats])
    # Ensure standard order
    preferred_order = ["All", "General", "OBC", "SC", "ST", "EWS"]
    ordered = [c for c in preferred_order if c in categories]
    # Add any remaining
    for c in sorted(categories):
        if c not in ordered:
            ordered.append(c)

    if not ordered:
        ordered = ["All", "General", "OBC", "SC", "ST", "EWS"]
    return ordered


@router.get(
    "/schemes/{scheme_id}/category-rules",
    response_model=List[SchemeCategoryRuleResponse],
    summary="Get category-specific eligibility rules",
    description="Retrieve eligibility condition criteria for specific caste or social categories.",
)
def get_scheme_category_rules(
    scheme_id: uuid.UUID,
    category: Optional[str] = Query(None, description="Optional category filter (e.g. 'OBC', 'SC', 'ST', 'General', 'EWS')"),
    db: Session = Depends(get_db),
):
    query = db.query(SchemeCategoryRule).filter(SchemeCategoryRule.scheme_id == scheme_id)
    if category:
        query = query.filter(SchemeCategoryRule.category.in_([category, "All"]))
    return query.all()


@router.get(
    "/schemes/{scheme_id}/documents",
    response_model=List[SchemeCategoryDocumentResponse],
    summary="Get category-specific document requirements",
    description="Retrieve required and optional documents for a scheme based on citizen category.",
)
def get_scheme_category_documents(
    scheme_id: uuid.UUID,
    category: Optional[str] = Query(None, description="Citizen category (e.g. 'General', 'OBC', 'SC', 'ST', 'EWS')"),
    db: Session = Depends(get_db),
):
    query = db.query(SchemeCategoryDocument).filter(SchemeCategoryDocument.scheme_id == scheme_id)
    if category and category.lower() != "all":
        query = query.filter(SchemeCategoryDocument.category.in_([category, "All"]))

    docs = query.all()
    # Check if a guide exists for each document_type
    guide_types = set(g[0] for g in db.query(DocumentGuide.document_type).all())

    results = []
    for doc in docs:
        resp = SchemeCategoryDocumentResponse.model_validate(doc)
        resp.has_guide = doc.document_type in guide_types
        results.append(resp)
    return results


@router.get(
    "/schemes/{scheme_id}/analytics",
    response_model=SchemeAnalyticsDatasetResponse,
    summary="Get official verified beneficiary analytics for a scheme",
    description="Returns aggregate government beneficiary figures, caste/category distributions, state distributions, and official citation. Strictly independent of JanMitra applicants.",
)
def get_scheme_analytics(
    scheme_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    dataset = db.query(SchemeAnalyticsDataset).filter(
        SchemeAnalyticsDataset.scheme_id == scheme_id,
        SchemeAnalyticsDataset.is_published == True,
    ).order_by(desc(SchemeAnalyticsDataset.dataset_version)).first()

    if not dataset:
        raise HTTPException(
            status_code=404,
            detail="No published official analytics dataset found for this scheme."
        )

    # Load breakdowns
    breakdowns = db.query(SchemeAnalyticsBreakdown).filter(
        SchemeAnalyticsBreakdown.dataset_id == dataset.id
    ).all()

    resp = SchemeAnalyticsDatasetResponse.model_validate(dataset)
    resp.breakdowns = [SchemeAnalyticsBreakdownResponse.model_validate(b) for b in breakdowns]
    return resp


@router.post(
    "/schemes/{scheme_id}/evaluate-category",
    response_model=CategoryRuleEvaluationResponse,
    summary="Evaluate category rules on-demand without persistent profile storage",
    description="Deterministically evaluates category criteria with on-demand consent. Never writes sensitive caste data to user profile.",
)
def evaluate_category_rules(
    scheme_id: uuid.UUID,
    request: CategoryRuleEvaluationRequest,
    db: Session = Depends(get_db),
):
    scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    rules = db.query(SchemeCategoryRule).filter(
        SchemeCategoryRule.scheme_id == scheme_id,
        SchemeCategoryRule.category.in_([request.category, "All"]),
    ).all()

    evaluations: List[CategoryRuleEvaluationItem] = []
    is_eligible = True
    special_notes: List[str] = []

    profile_data = request.profile_data or {}

    for rule in rules:
        actual_val = profile_data.get(rule.field)
        satisfied = True
        explanation = ""

        if actual_val is None:
            satisfied = True  # Neutral / unprovided
            explanation = f"Field '{rule.field}' not provided in evaluation request; condition assumed compliant pending document verification."
        else:
            try:
                op = rule.operator.lower()
                exp = rule.expected_value
                if op == "lte":
                    satisfied = float(actual_val) <= float(exp)
                    explanation = f"Value {actual_val} is {'<= ' + str(exp) if satisfied else 'exceeds threshold ' + str(exp)}."
                elif op == "gte":
                    satisfied = float(actual_val) >= float(exp)
                    explanation = f"Value {actual_val} is {'>= ' + str(exp) if satisfied else 'below threshold ' + str(exp)}."
                elif op == "eq":
                    satisfied = str(actual_val).strip().lower() == str(exp).strip().lower()
                    explanation = f"Value matches expected criteria." if satisfied else f"Expected '{exp}', received '{actual_val}'."
                elif op in ["contains", "in"]:
                    if isinstance(exp, list):
                        satisfied = actual_val in exp
                    else:
                        satisfied = str(exp).lower() in str(actual_val).lower()
                    explanation = "Criteria matched." if satisfied else "Criteria requirement not met."
            except Exception as e:
                satisfied = False
                explanation = f"Comparison error: {e}"

        if not satisfied:
            is_eligible = False

        if rule.special_conditions:
            special_notes.append(f"[{rule.category}] {rule.condition_name}: {rule.special_conditions}")

        evaluations.append(CategoryRuleEvaluationItem(
            condition_name=rule.condition_name,
            field=rule.field,
            operator=rule.operator,
            expected_value=rule.expected_value,
            actual_value=actual_val,
            is_satisfied=satisfied,
            explanation=explanation,
        ))

    return CategoryRuleEvaluationResponse(
        scheme_id=scheme_id,
        category=request.category,
        is_category_eligible=is_eligible,
        evaluations=evaluations,
        special_notes=special_notes,
    )


# Document Guides endpoints
@router.get(
    "/document-guides",
    response_model=List[DocumentGuideSummaryResponse],
    summary="List available official document preparation guides",
    description="Retrieve catalogue of official certificates and documents with step-by-step issuance guidance.",
)
def list_document_guides(
    db: Session = Depends(get_db),
):
    guides = db.query(DocumentGuide).order_by(DocumentGuide.document_name).all()
    return [DocumentGuideSummaryResponse.model_validate(g) for g in guides]


@router.get(
    "/document-guides/{document_type}",
    response_model=DocumentGuideResponse,
    summary="Get detailed step-by-step guide for an official document",
    description="Retrieve issuing authority by state, supporting documents, numbered online/offline steps, fees, timelines, and verified portal URLs.",
)
def get_document_guide_detail(
    document_type: str,
    db: Session = Depends(get_db),
):
    guide = db.query(DocumentGuide).filter(
        DocumentGuide.document_type == document_type
    ).first()

    if not guide:
        raise HTTPException(
            status_code=404,
            detail=f"Guidance not found for document type '{document_type}'."
        )

    return DocumentGuideResponse.model_validate(guide)


# ============================================================================
# ADMIN ENDPOINTS (Analytics Management, Lifecycle & Rules)
# ============================================================================

@admin_router.get(
    "/schemes/{scheme_id}/analytics",
    response_model=List[SchemeAnalyticsDatasetResponse],
    summary="Get all analytics datasets for a scheme (admin view)",
    description="Retrieve draft, pending, and published dataset versions with full breakdown data.",
)
def admin_get_scheme_analytics(
    scheme_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    datasets = db.query(SchemeAnalyticsDataset).filter(
        SchemeAnalyticsDataset.scheme_id == scheme_id
    ).order_by(desc(SchemeAnalyticsDataset.dataset_version)).all()

    results = []
    for ds in datasets:
        resp = SchemeAnalyticsDatasetResponse.model_validate(ds)
        breakdowns = db.query(SchemeAnalyticsBreakdown).filter(
            SchemeAnalyticsBreakdown.dataset_id == ds.id
        ).all()
        resp.breakdowns = [SchemeAnalyticsBreakdownResponse.model_validate(b) for b in breakdowns]
        results.append(resp)
    return results


@admin_router.post(
    "/schemes/{scheme_id}/analytics/import",
    response_model=SchemeAnalyticsDatasetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import official government beneficiary dataset",
    description="Admin uploads verified government dataset with breakdown dimensions. Created with status 'Pending Verification'.",
)
def admin_import_scheme_analytics(
    scheme_id: uuid.UUID,
    payload: SchemeAnalyticsImportRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    # Determine next dataset version
    latest_version = db.query(SchemeAnalyticsDataset.dataset_version).filter(
        SchemeAnalyticsDataset.scheme_id == scheme_id
    ).order_by(desc(SchemeAnalyticsDataset.dataset_version)).first()
    next_version = (latest_version[0] + 1) if latest_version else 1

    dataset = SchemeAnalyticsDataset(
        scheme_id=scheme_id,
        source_name=payload.source_name,
        report_title=payload.report_title,
        source_url=payload.source_url,
        source_publication_date=datetime.now(timezone.utc),
        reporting_period=payload.reporting_period,
        geographic_scope=payload.geographic_scope,
        metric_type=payload.metric_type,
        metric_definition=payload.metric_definition,
        total_beneficiaries=payload.total_beneficiaries,
        dataset_version=next_version,
        verification_status="Pending Verification",
        is_published=False,
        notes=payload.notes,
    )
    db.add(dataset)
    db.flush()

    # Add breakdowns
    for b in payload.breakdowns:
        breakdown = SchemeAnalyticsBreakdown(
            dataset_id=dataset.id,
            dimension=b.dimension,
            category_name=b.category_name,
            metric_value=b.metric_value,
            percentage=b.percentage,
            notes=b.notes,
        )
        db.add(breakdown)

    # Audit log
    audit = SchemeAnalyticsAuditLog(
        dataset_id=dataset.id,
        scheme_id=scheme_id,
        admin_id=admin.id,
        action="imported",
        details={
            "total_beneficiaries": dataset.total_beneficiaries,
            "reporting_period": dataset.reporting_period,
            "source_name": dataset.source_name,
            "breakdown_count": len(payload.breakdowns),
        }
    )
    db.add(audit)
    db.commit()
    db.refresh(dataset)

    resp = SchemeAnalyticsDatasetResponse.model_validate(dataset)
    breakdowns = db.query(SchemeAnalyticsBreakdown).filter(
        SchemeAnalyticsBreakdown.dataset_id == dataset.id
    ).all()
    resp.breakdowns = [SchemeAnalyticsBreakdownResponse.model_validate(b) for b in breakdowns]
    return resp


@admin_router.post(
    "/schemes/{scheme_id}/analytics/{dataset_id}/validate",
    response_model=SchemeAnalyticsDatasetResponse,
    summary="Validate imported analytics dataset",
    description="Admin validates the consistency and official citation of a dataset.",
)
def admin_validate_dataset(
    scheme_id: uuid.UUID,
    dataset_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    dataset = db.query(SchemeAnalyticsDataset).filter(
        SchemeAnalyticsDataset.id == dataset_id,
        SchemeAnalyticsDataset.scheme_id == scheme_id,
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    dataset.verification_status = "Verified"
    dataset.last_verified_at = datetime.now(timezone.utc)

    audit = SchemeAnalyticsAuditLog(
        dataset_id=dataset.id,
        scheme_id=scheme_id,
        admin_id=admin.id,
        action="validated",
        details={"status": "Verified", "verified_at": str(dataset.last_verified_at)},
    )
    db.add(audit)
    db.commit()
    db.refresh(dataset)

    resp = SchemeAnalyticsDatasetResponse.model_validate(dataset)
    breakdowns = db.query(SchemeAnalyticsBreakdown).filter(
        SchemeAnalyticsBreakdown.dataset_id == dataset.id
    ).all()
    resp.breakdowns = [SchemeAnalyticsBreakdownResponse.model_validate(b) for b in breakdowns]
    return resp


@admin_router.post(
    "/schemes/{scheme_id}/analytics/{dataset_id}/publish",
    response_model=SchemeAnalyticsDatasetResponse,
    summary="Publish analytics dataset for citizen viewing",
    description="Marks dataset as active and published, replacing any prior published version.",
)
def admin_publish_dataset(
    scheme_id: uuid.UUID,
    dataset_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    dataset = db.query(SchemeAnalyticsDataset).filter(
        SchemeAnalyticsDataset.id == dataset_id,
        SchemeAnalyticsDataset.scheme_id == scheme_id,
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Unpublish existing published datasets for this scheme
    db.query(SchemeAnalyticsDataset).filter(
        SchemeAnalyticsDataset.scheme_id == scheme_id,
        SchemeAnalyticsDataset.id != dataset.id,
    ).update({"is_published": False})

    dataset.is_published = True
    dataset.verification_status = "Verified"
    dataset.published_at = datetime.now(timezone.utc)
    if not dataset.last_verified_at:
        dataset.last_verified_at = dataset.published_at

    audit = SchemeAnalyticsAuditLog(
        dataset_id=dataset.id,
        scheme_id=scheme_id,
        admin_id=admin.id,
        action="published",
        details={"published_at": str(dataset.published_at)},
    )
    db.add(audit)
    db.commit()
    db.refresh(dataset)

    resp = SchemeAnalyticsDatasetResponse.model_validate(dataset)
    breakdowns = db.query(SchemeAnalyticsBreakdown).filter(
        SchemeAnalyticsBreakdown.dataset_id == dataset.id
    ).all()
    resp.breakdowns = [SchemeAnalyticsBreakdownResponse.model_validate(b) for b in breakdowns]
    return resp


@admin_router.post(
    "/schemes/{scheme_id}/analytics/{dataset_id}/unpublish",
    response_model=SchemeAnalyticsDatasetResponse,
    summary="Unpublish analytics dataset",
    description="Removes dataset from public citizen view.",
)
def admin_unpublish_dataset(
    scheme_id: uuid.UUID,
    dataset_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    dataset = db.query(SchemeAnalyticsDataset).filter(
        SchemeAnalyticsDataset.id == dataset_id,
        SchemeAnalyticsDataset.scheme_id == scheme_id,
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    dataset.is_published = False

    audit = SchemeAnalyticsAuditLog(
        dataset_id=dataset.id,
        scheme_id=scheme_id,
        admin_id=admin.id,
        action="unpublished",
        details={"unpublished_at": str(datetime.now(timezone.utc))},
    )
    db.add(audit)
    db.commit()
    db.refresh(dataset)

    resp = SchemeAnalyticsDatasetResponse.model_validate(dataset)
    breakdowns = db.query(SchemeAnalyticsBreakdown).filter(
        SchemeAnalyticsBreakdown.dataset_id == dataset.id
    ).all()
    resp.breakdowns = [SchemeAnalyticsBreakdownResponse.model_validate(b) for b in breakdowns]
    return resp


@admin_router.get(
    "/schemes/{scheme_id}/analytics/history",
    response_model=List[SchemeAnalyticsAuditLogResponse],
    summary="Get analytics audit log history",
    description="Retrieve chronological record of imports, validations, and publication changes.",
)
def admin_get_analytics_audit_history(
    scheme_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    logs = db.query(SchemeAnalyticsAuditLog).filter(
        SchemeAnalyticsAuditLog.scheme_id == scheme_id
    ).order_by(desc(SchemeAnalyticsAuditLog.created_at)).all()

    return [SchemeAnalyticsAuditLogResponse.model_validate(log) for log in logs]


# Category Rules Admin CRUD
@admin_router.post(
    "/schemes/{scheme_id}/category-rules",
    response_model=SchemeCategoryRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create scheme category eligibility rule",
)
def admin_create_category_rule(
    scheme_id: uuid.UUID,
    payload: SchemeCategoryRuleBase,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    rule = SchemeCategoryRule(
        scheme_id=scheme_id,
        **payload.model_dump(),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return SchemeCategoryRuleResponse.model_validate(rule)


@admin_router.delete(
    "/schemes/category-rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete scheme category rule",
)
def admin_delete_category_rule(
    rule_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    rule = db.query(SchemeCategoryRule).filter(SchemeCategoryRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
    return None
