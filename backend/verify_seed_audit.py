import sys
from app.core.database import SessionLocal
from app.models.scheme_intelligence import SchemeAnalyticsDataset, SchemeAnalyticsBreakdown, SchemeCategoryRule

db = SessionLocal()
print("=== DATASET VERIFICATION ===")
for d in db.query(SchemeAnalyticsDataset).all():
    print(f"Scheme ID: {d.scheme_id} | Report: {d.report_title} | Published: {d.is_published} | Status: {d.verification_status} | Scope: {d.geographic_scope} | Metric: {d.metric_type}")

caste_count = db.query(SchemeAnalyticsBreakdown).filter(SchemeAnalyticsBreakdown.dimension == "caste_category").count()
print(f"Total remaining caste_category breakdowns: {caste_count}")

print("=== CATEGORY RULES VERIFICATION ===")
for r in db.query(SchemeCategoryRule).all():
    print(f"Category: {r.category} | Rule: {r.condition_name} | Scope: {r.geographic_scope} | Status: {r.verification_status}")

db.close()
