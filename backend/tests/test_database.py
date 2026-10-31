import uuid
from datetime import date, datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import inspect

from app.main import app
from app.core.config import settings
from app.core.database import Base, check_database_connection
from app.models import (
    User,
    UserProfile,
    Scheme,
    DocumentMetadata,
    Assessment,
    Application,
    Subscription,
    Notification,
    APPLICATION_STATUSES,
    PLAN_TYPES,
    BILLING_CYCLES,
)

client = TestClient(app)


class TestDatabaseModelsMetadata:
    """Verifies that all 8 approved models are properly declared and mapped to SQLAlchemy metadata."""

    def test_all_expected_tables_registered(self):
        expected_tables = {
            "users",
            "user_profiles",
            "schemes",
            "document_metadata",
            "assessments",
            "applications",
            "subscriptions",
            "notifications",
        }
        registered_tables = set(Base.metadata.tables.keys())
        assert expected_tables.issubset(registered_tables), (
            f"Missing tables: {expected_tables - registered_tables}"
        )

    def test_user_model_schema(self):
        table = Base.metadata.tables["users"]
        assert "id" in table.c
        assert isinstance(table.c.id.type, UUID)
        assert table.c.id.primary_key
        assert "role" in table.c
        assert "email" in table.c
        assert table.c.email.unique
        assert "mobile_number" in table.c
        assert table.c.mobile_number.unique
        assert "is_active" in table.c
        assert not table.c.is_active.nullable
        assert "created_at" in table.c
        assert "updated_at" in table.c

    def test_user_profile_relationship_and_privacy(self):
        table = Base.metadata.tables["user_profiles"]
        assert "user_id" in table.c
        assert table.c.user_id.unique
        assert not table.c.user_id.nullable

        # Verify foreign key to users.id
        fk = list(table.c.user_id.foreign_keys)[0]
        assert fk.target_fullname == "users.id"

        # Privacy Architecture Check: Aadhaar is deliberately not stored
        assert "aadhaar" not in table.c
        assert "aadhaar_number" not in table.c

        # Socioeconomic fields
        assert "full_name" in table.c
        assert "date_of_birth" in table.c
        assert "state" in table.c
        assert "district" in table.c
        assert "residence_type" in table.c
        assert "annual_family_income" in table.c

    def test_scheme_model_schema(self):
        table = Base.metadata.tables["schemes"]
        assert "scheme_name" in table.c
        assert "short_description" in table.c
        assert "category" in table.c
        assert "description" in table.c
        assert "department" in table.c
        assert "state_applicability" in table.c
        assert "eligibility_summary" in table.c
        assert "benefits" in table.c
        assert "eligibility_criteria" in table.c
        assert "required_profile_fields" in table.c
        assert "application_process" in table.c
        assert "required_documents" in table.c
        assert "official_source_url" in table.c
        assert "official_application_url" in table.c
        assert "source_last_verified_at" in table.c
        assert "source_verification_details" in table.c
        assert "status" in table.c
        assert "is_active" in table.c
        assert "is_demo_data" in table.c

    def test_document_metadata_storage_separation(self):
        table = Base.metadata.tables["document_metadata"]
        assert "user_id" in table.c
        fk = list(table.c.user_id.foreign_keys)[0]
        assert fk.target_fullname == "users.id"

        # Check metadata fields
        assert "document_type" in table.c
        assert "original_filename" in table.c
        assert "storage_reference" in table.c
        assert "mime_type" in table.c
        assert "file_size" in table.c
        assert "upload_status" in table.c

        # Privacy Check: No raw binary blob column in PostgreSQL
        assert "file_data" not in table.c
        assert "binary_content" not in table.c
        assert "content" not in table.c

    def test_assessment_jsonb_and_advisory_nature(self):
        table = Base.metadata.tables["assessments"]
        assert "user_id" in table.c
        assert "scheme_id" in table.c
        assert "assessment_type" in table.c
        assert "result_data" in table.c
        assert isinstance(table.c.result_data.type, JSONB)
        assert "overall_readiness_score" in table.c

    def test_application_manual_status_values(self):
        table = Base.metadata.tables["applications"]
        assert "user_id" in table.c
        assert "scheme_id" in table.c
        assert "application_reference_number" in table.c
        assert "submission_date" in table.c
        assert "status" in table.c

        expected_statuses = [
            "Submitted",
            "Under Review",
            "Pending",
            "Document Verification",
            "Approved",
            "Rejected",
            "Completed",
        ]
        assert APPLICATION_STATUSES == expected_statuses

    def test_subscription_pricing_and_plans(self):
        table = Base.metadata.tables["subscriptions"]
        assert "user_id" in table.c
        assert "plan_type" in table.c
        assert "billing_cycle" in table.c
        assert "status" in table.c
        assert "start_date" in table.c
        assert "end_date" in table.c

        assert PLAN_TYPES == ["free", "premium"]
        assert BILLING_CYCLES == ["monthly", "yearly"]

    def test_notification_model_schema(self):
        table = Base.metadata.tables["notifications"]
        assert "user_id" in table.c
        assert "title" in table.c
        assert "message" in table.c
        assert "notification_type" in table.c
        assert "scheduled_at" in table.c
        assert "is_read" in table.c


class TestDatabaseHealthApi:
    """Verifies the health check API endpoints and secure failure handling."""

    def test_root_endpoint_includes_db_link(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("health_check") == "/health"
        assert data.get("database_health") == "/health/database"

    def test_general_health_endpoint_still_operational(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"

    def test_database_health_endpoint_safe_response(self):
        response = client.get("/health/database")
        data = response.json()

        # Database is either online (200) or gracefully reports offline (503)
        assert response.status_code in (200, 503)

        if response.status_code == 200:
            assert data.get("status") == "healthy"
            assert data.get("database") == "connected"
            assert data.get("database_type") == "PostgreSQL"
        else:
            assert data.get("status") == "unhealthy"
            assert data.get("database") == "disconnected"
            assert data.get("database_type") == "PostgreSQL"

        # Security check: Password or credentials must never appear in response keys or sensitive values
        assert "password" not in data
        assert "secret" not in data
        assert "connection_string" not in data
        assert "url" not in data
        assert "postgres://" not in response.text.lower()
        assert "psycopg://" not in response.text.lower()
