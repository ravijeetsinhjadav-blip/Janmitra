import os
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.core.config import settings
from app.core.database import Base
from app.models.user import User
from app.models.profile import UserProfile
from app.models.otp import OTPChallenge
from app.models.session import UserSession
from app.models.account_deletion import AccountDeletionRequest
from app.models.assessment import Assessment
from app.core.security import hash_token


class TestPostgresDialectCompatibility:
    """Verifies that all Phase 1-3 SQLAlchemy models generate valid PostgreSQL DDL.
    
    This verifies PostgreSQL dialect compatibility directly with PostgresqlImpl,
    testing UUID, JSONB, TIMESTAMPTZ, and foreign keys.
    """

    def test_all_models_compile_for_postgresql(self):
        pg_dialect = postgresql.dialect()
        tables = [
            "users",
            "user_profiles",
            "schemes",
            "document_metadata",
            "assessments",
            "applications",
            "subscriptions",
            "user_monthly_quotas",
            "payment_transactions",
            "webhook_events",
            "notifications",
            "otp_challenges",
            "user_sessions",
            "account_deletion_requests",
        ]

        for table_name in tables:
            assert table_name in Base.metadata.tables, f"Missing table {table_name}"
            table = Base.metadata.tables[table_name]
            ddl_stmt = CreateTable(table).compile(dialect=pg_dialect)
            compiled_sql = str(ddl_stmt)
            assert "CREATE TABLE" in compiled_sql
            assert table_name in compiled_sql

    def test_postgresql_uuid_and_jsonb_types(self):
        pg_dialect = postgresql.dialect()
        assessments_table = Base.metadata.tables["assessments"]
        ddl = str(CreateTable(assessments_table).compile(dialect=pg_dialect))
        assert "UUID" in ddl
        assert "JSONB" in ddl

    def test_postgresql_foreign_key_cascades(self):
        pg_dialect = postgresql.dialect()
        sessions_table = Base.metadata.tables["user_sessions"]
        ddl = str(CreateTable(sessions_table).compile(dialect=pg_dialect))
        assert "FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE" in ddl

        deletion_table = Base.metadata.tables["account_deletion_requests"]
        del_ddl = str(CreateTable(deletion_table).compile(dialect=pg_dialect))
        assert "FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE" in del_ddl

    def test_postgresql_payment_and_quota_ledger_ddl(self):
        pg_dialect = postgresql.dialect()
        quota_table = Base.metadata.tables["user_monthly_quotas"]
        quota_ddl = str(CreateTable(quota_table).compile(dialect=pg_dialect))
        assert "uq_user_monthly_quota UNIQUE (user_id, year_month)" in quota_ddl
        assert "guidance_sessions_used INTEGER" in quota_ddl
        assert "doc_analyses_used INTEGER" in quota_ddl

        tx_table = Base.metadata.tables["payment_transactions"]
        tx_ddl = str(CreateTable(tx_table).compile(dialect=pg_dialect))
        assert "amount_refunded NUMERIC(10, 2)" in tx_ddl
        assert "dispute_status VARCHAR(50)" in tx_ddl
        assert "refunds_log JSONB" in tx_ddl

        wh_table = Base.metadata.tables["webhook_events"]
        wh_ddl = str(CreateTable(wh_table).compile(dialect=pg_dialect))
        assert "event_id VARCHAR(100)" in wh_ddl
        assert "payload_summary JSONB" in wh_ddl

        doc_table = Base.metadata.tables["document_metadata"]
        doc_ddl = str(CreateTable(doc_table).compile(dialect=pg_dialect))
        assert "processing_token UUID" in doc_ddl
        assert "lease_expires_at TIMESTAMP WITH TIME ZONE" in doc_ddl


class TestPostgresLiveIntegration:
    """Live PostgreSQL integration tests.
    
    Connects to a PostgreSQL instance if reachable, verifying persistence,
    sessions, OTPs, deletion requests, and timezone compatibility.
    Skips cleanly if PostgreSQL daemon is offline on port 5432.
    """

    @pytest.fixture(scope="class")
    def pg_engine(self):
        test_pg_url = os.environ.get("TEST_POSTGRES_URL", settings.DATABASE_URL)
        try:
            engine = create_engine(
                test_pg_url,
                connect_args={"connect_timeout": 2},
                pool_pre_ping=True,
            )
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine
        except Exception:
            pytest.skip(
                f"PostgreSQL server is not reachable at {test_pg_url}. "
                "Skipping live PostgreSQL integration tests."
            )

    def test_live_postgres_otp_and_session_persistence(self, pg_engine):
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=pg_engine)
        db = SessionLocal()

        try:
            # Create a test citizen
            test_user = User(
                role="citizen",
                mobile_number="+919999988888",
                is_active=True,
            )
            db.add(test_user)
            db.flush()

            # Create OTP challenge
            now = datetime.now(timezone.utc)
            otp_record = OTPChallenge(
                mobile_number="+919999988888",
                hashed_otp=hash_token("654321"),
                purpose="auth",
                expires_at=now + timedelta(minutes=5),
                attempts=0,
                max_attempts=3,
                is_verified=False,
            )
            db.add(otp_record)

            # Create User session with hashed refresh token
            token_hash = hash_token("test_refresh_token_entropy_string")
            session_record = UserSession(
                user_id=test_user.id,
                token_hash=token_hash,
                device_info="Postgres Integration Test Client",
                ip_address="127.0.0.1",
                expires_at=now + timedelta(days=30),
                is_revoked=False,
            )
            db.add(session_record)

            # Create Account deletion request
            deletion_request = AccountDeletionRequest(
                user_id=test_user.id,
                status="pending",
                reason="Integration testing",
                scheduled_for=now + timedelta(days=30),
            )
            db.add(deletion_request)
            db.commit()

            # Query back and verify persistence
            queried_session = db.query(UserSession).filter(UserSession.token_hash == token_hash).first()
            assert queried_session is not None
            assert queried_session.user_id == test_user.id
            assert queried_session.is_revoked is False

            queried_otp = db.query(OTPChallenge).filter(OTPChallenge.mobile_number == "+919999988888").first()
            assert queried_otp is not None
            assert queried_otp.is_verified is False

            queried_del = db.query(AccountDeletionRequest).filter(AccountDeletionRequest.user_id == test_user.id).first()
            assert queried_del is not None
            assert queried_del.status == "pending"

        finally:
            db.rollback()
            db.close()


class TestPostgresConcurrencyLive:
    """Rigorous multi-threaded concurrency verification on live PostgreSQL (SEC-04, SEC-05, SEC-06).
    
    Uses concurrent.futures.ThreadPoolExecutor against a real PostgreSQL connection pool.
    Skips cleanly if PostgreSQL daemon is offline.
    """

    @pytest.fixture(scope="class")
    def pg_sessionmaker(self):
        test_pg_url = os.environ.get("TEST_POSTGRES_URL", settings.DATABASE_URL)
        try:
            engine = create_engine(
                test_pg_url,
                connect_args={"connect_timeout": 2},
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=5,
            )
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            from sqlalchemy.orm import sessionmaker
            return sessionmaker(bind=engine)
        except Exception:
            pytest.skip(
                f"PostgreSQL server is not reachable at {test_pg_url}. "
                "Skipping live PostgreSQL concurrency tests."
            )

    def test_concurrent_monthly_quota_record_initialization(self, pg_sessionmaker):
        """Verify 5 concurrent threads initializing UserMonthlyQuota record for the same user."""
        from concurrent.futures import ThreadPoolExecutor
        from app.services.subscription_service import SubscriptionService

        db_init = pg_sessionmaker()
        test_user = User(
            id=uuid.uuid4(),
            role="citizen",
            mobile_number=f"99{uuid.uuid4().int % 100000000:08d}",
            is_active=True,
        )
        db_init.add(test_user)
        db_init.commit()
        db_init.close()

        def init_quota(idx):
            db = pg_sessionmaker()
            try:
                rec = SubscriptionService.get_or_create_monthly_quota_record(db, test_user.id, for_update=True)
                return rec is not None
            finally:
                db.close()

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(init_quota, range(5)))

        assert all(results)
        # Verify exactly one record exists in DB
        db_check = pg_sessionmaker()
        now = datetime.now(timezone.utc)
        ym = f"{now.year:04d}-{now.month:02d}"
        from app.models.subscription import UserMonthlyQuota
        records = db_check.query(UserMonthlyQuota).filter(
            UserMonthlyQuota.user_id == test_user.id,
            UserMonthlyQuota.year_month == ym,
        ).all()
        assert len(records) == 1
        db_check.close()

    def test_concurrent_document_quota_reservations_respect_limit(self, pg_sessionmaker):
        """Citizen has limit 3, currently used 2. 5 concurrent requests try to reserve the last slot."""
        from concurrent.futures import ThreadPoolExecutor
        from app.services.subscription_service import SubscriptionService
        from app.models.document import DocumentMetadata, DocumentProcessingStatus

        db_init = pg_sessionmaker()
        test_user = User(
            id=uuid.uuid4(),
            role="citizen",
            mobile_number=f"99{uuid.uuid4().int % 100000000:08d}",
            is_active=True,
        )
        db_init.add(test_user)
        db_init.commit()

        # Seed 2 completed documents
        for i in range(2):
            doc = DocumentMetadata(
                id=uuid.uuid4(),
                user_id=test_user.id,
                document_type="income_certificate",
                original_filename=f"doc_{i}.pdf",
                storage_reference=f"/vault/{test_user.id}/doc_{i}.pdf",
                mime_type="application/pdf",
                file_size=1024,
                ocr_status=DocumentProcessingStatus.OCR_COMPLETED,
            )
            db_init.add(doc)
        db_init.commit()
        db_init.close()

        def try_reserve(idx):
            db = pg_sessionmaker()
            try:
                SubscriptionService.reserve_document_analysis_quota(db, test_user.id)
                # Create in-flight doc
                doc_in_flight = DocumentMetadata(
                    id=uuid.uuid4(),
                    user_id=test_user.id,
                    document_type="income_certificate",
                    original_filename=f"concurrent_{idx}.pdf",
                    storage_reference=f"/vault/{test_user.id}/concurrent_{idx}.pdf",
                    mime_type="application/pdf",
                    file_size=1024,
                    ocr_status=DocumentProcessingStatus.PROCESSING,
                )
                db.add(doc_in_flight)
                db.commit()
                return "SUCCESS"
            except Exception as e:
                db.rollback()
                if "403" in str(e) or "quota reached" in str(e).lower():
                    return "BLOCKED_QUOTA"
                return f"ERROR: {e}"
            finally:
                db.close()

        with ThreadPoolExecutor(max_workers=5) as executor:
            outcomes = list(executor.map(try_reserve, range(5)))

        # Exactly 1 request should succeed to reach limit 3, exactly 4 should be BLOCKED_QUOTA
        success_count = outcomes.count("SUCCESS")
        blocked_count = outcomes.count("BLOCKED_QUOTA")
        assert success_count == 1
        assert blocked_count == 4

