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
            phone = f"+9199{uuid.uuid4().int % 100000000:08d}"
            test_user = User(
                role="citizen",
                mobile_number=phone,
                is_active=True,
            )
            db.add(test_user)
            db.flush()

            # Create OTP challenge
            now = datetime.now(timezone.utc)
            otp_record = OTPChallenge(
                mobile_number=phone,
                hashed_otp=hash_token("654321"),
                purpose="auth",
                expires_at=now + timedelta(minutes=5),
                attempts=0,
                max_attempts=3,
                is_verified=False,
            )
            db.add(otp_record)

            # Create User session with hashed refresh token
            token_hash = hash_token(f"test_refresh_token_entropy_string_{uuid.uuid4().hex}")
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

            queried_otp = db.query(OTPChallenge).filter(OTPChallenge.mobile_number == phone).first()
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

        user_id = uuid.uuid4()
        db_init = pg_sessionmaker()
        test_user = User(
            id=user_id,
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
                rec = SubscriptionService.get_or_create_monthly_quota_record(db, user_id, for_update=True)
                db.commit()
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
            UserMonthlyQuota.user_id == user_id,
            UserMonthlyQuota.year_month == ym,
        ).all()
        assert len(records) == 1
        db_check.close()

    def test_concurrent_document_quota_reservations_respect_limit(self, pg_sessionmaker):
        """Citizen has limit 3, currently used 2. 5 concurrent requests try to reserve the last slot."""
        from concurrent.futures import ThreadPoolExecutor
        from app.services.subscription_service import SubscriptionService
        from app.models.document import DocumentMetadata, DocumentProcessingStatus

        user_id = uuid.uuid4()
        db_init = pg_sessionmaker()
        test_user = User(
            id=user_id,
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
                user_id=user_id,
                document_type="income_certificate",
                original_filename=f"doc_{i}.pdf",
                storage_reference=f"/vault/{user_id}/doc_{i}.pdf",
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
                SubscriptionService.reserve_document_analysis_quota(db, user_id)
                # Create in-flight doc
                doc_in_flight = DocumentMetadata(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    document_type="income_certificate",
                    original_filename=f"concurrent_{idx}.pdf",
                    storage_reference=f"/vault/{user_id}/concurrent_{idx}.pdf",
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

    def test_concurrent_document_retry_requests(self, pg_sessionmaker):
        """AUD-06: 5 concurrent retry attempts invoking actual DocumentService.retry_ocr().

        Row-lock serialization in DocumentService.retry_ocr guarantees exactly 1
        transitions to PROCESSING under exclusive lease ownership, while all
        concurrent competitors receive 409 Conflict.
        """
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from unittest.mock import patch
        from fastapi import HTTPException
        from sqlalchemy import func
        from app.models.document import DocumentMetadata, DocumentProcessingStatus
        from app.services.document_service import DocumentService
        from app.services.subscription_service import SubscriptionService
        from app.services.ocr_service import OCRResult

        user_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        db_init = pg_sessionmaker()

        test_user = User(
            id=user_id,
            role="citizen",
            mobile_number=f"99{uuid.uuid4().int % 100000000:08d}",
            is_active=True,
        )
        db_init.add(test_user)

        failed_doc = DocumentMetadata(
            id=doc_id,
            user_id=user_id,
            document_type="income_certificate",
            original_filename="failed_doc.pdf",
            storage_reference=f"/vault/{user_id}/failed_doc.pdf",
            mime_type="application/pdf",
            file_size=1024,
            ocr_status=DocumentProcessingStatus.OCR_FAILED,
        )
        db_init.add(failed_doc)
        db_init.commit()
        db_init.close()

        winner_in_ocr = threading.Event()
        allow_ocr_to_finish = threading.Event()

        def fake_get_file_bytes(storage_ref):
            return b"%PDF-1.4 test binary content"

        def fake_process_document(*args, **kwargs):
            # Signal that the winning worker has acquired lease, committed PROCESSING, and started OCR
            winner_in_ocr.set()
            # Deterministically hold lease until competitors have raced and been rejected with 409
            allow_ocr_to_finish.wait(timeout=10.0)
            return OCRResult(
                extracted_text="Income: 100000",
                confidence=0.95,
                metadata={"engine": "mock_ocr"},
                status=DocumentProcessingStatus.OCR_COMPLETED,
                manual_review_required=False,
            )

        def attempt_retry(idx):
            db = pg_sessionmaker()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                DocumentService.retry_ocr(
                    db=db,
                    document_id=doc_id,
                    user=user,
                )
                return "ACQUIRED"
            except HTTPException as http_exc:
                if http_exc.status_code == 409:
                    return "CONFLICT_409"
                return f"HTTP_{http_exc.status_code}"
            except Exception as exc:
                return f"ERROR_{exc}"
            finally:
                db.close()

        with patch("app.services.document_service.storage_service.get_file_bytes", side_effect=fake_get_file_bytes), \
             patch("app.services.document_service.ocr_service.process_document", side_effect=fake_process_document):

            with ThreadPoolExecutor(max_workers=5) as executor:
                # Launch all 5 concurrent retry attempts simultaneously
                futures = [executor.submit(attempt_retry, i) for i in range(5)]

                # Deterministically wait for winner to acquire lease and enter OCR
                assert winner_in_ocr.wait(timeout=5.0), "Winning thread failed to acquire lease"

                # Check PostgreSQL database while lease is actively held
                db_verify = pg_sessionmaker()
                in_flight_doc = db_verify.query(DocumentMetadata).filter(DocumentMetadata.id == doc_id).first()
                assert in_flight_doc.ocr_status == DocumentProcessingStatus.PROCESSING
                assert in_flight_doc.processing_token is not None
                assert in_flight_doc.lease_expires_at is not None
                assert in_flight_doc.lease_expires_at > datetime.now(timezone.utc)

                # Verify quota: exactly 1 in-flight reservation exists
                now = datetime.now(timezone.utc)
                month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
                in_flight_count = (
                    db_verify.query(func.count(DocumentMetadata.id))
                    .filter(
                        DocumentMetadata.user_id == user_id,
                        DocumentMetadata.ocr_status == DocumentProcessingStatus.PROCESSING,
                        DocumentMetadata.created_at >= month_start,
                    )
                    .scalar()
                )
                assert in_flight_count == 1
                db_verify.close()

                # Collect the 4 competing futures while winner remains blocked
                competitor_outcomes = []
                remaining_futures = set(futures)
                for f in as_completed(remaining_futures):
                    competitor_outcomes.append(f.result(timeout=10.0))
                    remaining_futures.remove(f)
                    if len(competitor_outcomes) == 4:
                        break

                # Step 3: Verify all four completed results are CONFLICT_409 while winner remains blocked
                assert len(competitor_outcomes) == 4
                assert competitor_outcomes == ["CONFLICT_409", "CONFLICT_409", "CONFLICT_409", "CONFLICT_409"]

                # Step 4: Only after these four conflicts are verified, release winner to complete OCR
                allow_ocr_to_finish.set()

                # Step 5: Collect the winner's result and verify it is ACQUIRED
                assert len(remaining_futures) == 1
                winning_future = remaining_futures.pop()
                winner_result = winning_future.result(timeout=10.0)
                assert winner_result == "ACQUIRED"

        # Final DB check: document successfully finalized to OCR_COMPLETED
        db_final = pg_sessionmaker()
        final_doc = db_final.query(DocumentMetadata).filter(DocumentMetadata.id == doc_id).first()
        assert final_doc.ocr_status == DocumentProcessingStatus.OCR_COMPLETED
        assert final_doc.processing_token is None  # Token released upon successful finalization (AUD-04)
        assert final_doc.lease_expires_at is None
        assert final_doc.ocr_extracted_text == "Income: 100000"

        # Quota successfully finalized to 1 completed analysis
        quota_final = SubscriptionService.get_quota_status(db_final, user_id)
        assert quota_final.ai_document_analyses_used == 1
        db_final.close()

    def test_live_postgres_lease_renewal_vs_stale_recovery(self, pg_sessionmaker):
        """AUD-03: Active worker with renewed lease is preserved on live PostgreSQL;
        crashed worker with expired lease is auto-healed to OCR_FAILED.
        """
        from app.models.document import DocumentMetadata, DocumentProcessingStatus
        from app.services.subscription_service import SubscriptionService

        user_id = uuid.uuid4()
        active_doc_id = uuid.uuid4()
        stale_doc_id = uuid.uuid4()
        active_token = uuid.uuid4()
        stale_token = uuid.uuid4()

        db = pg_sessionmaker()
        test_user = User(
            id=user_id,
            role="citizen",
            mobile_number=f"99{uuid.uuid4().int % 100000000:08d}",
            is_active=True,
        )
        db.add(test_user)

        now = datetime.now(timezone.utc)
        # Active document: started 6 minutes ago, but heartbeat renewed lease to now + 4 mins
        active_doc = DocumentMetadata(
            id=active_doc_id,
            user_id=user_id,
            document_type="income_certificate",
            original_filename="active.pdf",
            storage_reference=f"/vault/{user_id}/active.pdf",
            mime_type="application/pdf",
            file_size=2048,
            ocr_status=DocumentProcessingStatus.PROCESSING,
            processing_token=active_token,
            created_at=now - timedelta(minutes=6),
            lease_expires_at=now + timedelta(minutes=4),
        )
        # Stale document: started 10 minutes ago, lease expired 5 minutes ago
        stale_doc = DocumentMetadata(
            id=stale_doc_id,
            user_id=user_id,
            document_type="income_certificate",
            original_filename="stale.pdf",
            storage_reference=f"/vault/{user_id}/stale.pdf",
            mime_type="application/pdf",
            file_size=2048,
            ocr_status=DocumentProcessingStatus.PROCESSING,
            processing_token=stale_token,
            created_at=now - timedelta(minutes=10),
            lease_expires_at=now - timedelta(minutes=5),
        )
        db.add_all([active_doc, stale_doc])
        db.commit()

        # Run auto-heal
        healed_count = SubscriptionService.auto_heal_stale_processing_documents(db, user_id)
        assert healed_count == 1  # Only stale doc healed!

        # Verify active doc remains in PROCESSING with its token intact
        db.refresh(active_doc)
        assert active_doc.ocr_status == DocumentProcessingStatus.PROCESSING
        assert active_doc.processing_token == active_token

        # Verify stale doc is marked OCR_FAILED and token revoked
        db.refresh(stale_doc)
        assert stale_doc.ocr_status == DocumentProcessingStatus.OCR_FAILED
        assert stale_doc.processing_token is None
        assert stale_doc.lease_expires_at is None
        db.close()

    def test_live_postgres_old_worker_finalization_after_token_invalidation(self, pg_sessionmaker):
        """AUD-04: Late worker finishing after token invalidation is rejected and cannot consume quota."""
        from app.models.document import DocumentMetadata, DocumentProcessingStatus
        from app.services.subscription_service import SubscriptionService

        user_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        old_token = uuid.uuid4()

        db = pg_sessionmaker()
        test_user = User(
            id=user_id,
            role="citizen",
            mobile_number=f"99{uuid.uuid4().int % 100000000:08d}",
            is_active=True,
        )
        db.add(test_user)

        # Create document that was auto-healed after crash (status OCR_FAILED, token cleared)
        doc = DocumentMetadata(
            id=doc_id,
            user_id=user_id,
            document_type="income_certificate",
            original_filename="crashed.pdf",
            storage_reference=f"/vault/{user_id}/crashed.pdf",
            mime_type="application/pdf",
            file_size=2048,
            ocr_status=DocumentProcessingStatus.OCR_FAILED,
            processing_token=None,  # Token was revoked
            lease_expires_at=None,
        )
        db.add(doc)
        db.commit()

        # Zombie worker awakes and tries to finalize with old_token
        finalized = SubscriptionService.finalize_document_analysis(
            db=db,
            user_id=user_id,
            doc_id=doc_id,
            processing_token=old_token,
        )
        assert finalized is False

        # Quota remains 0
        quota = SubscriptionService.get_quota_status(db, user_id)
        assert quota.ai_document_analyses_used == 0

        # Document record remains unchanged
        db.refresh(doc)
        assert doc.ocr_status == DocumentProcessingStatus.OCR_FAILED
        db.close()

