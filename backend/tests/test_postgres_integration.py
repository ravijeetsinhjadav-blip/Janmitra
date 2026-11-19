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
from app.models.session import UserSession
from app.models.password_reset import PasswordResetToken
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
            "application_status_history",
            "application_reminders",
            "subscriptions",
            "user_monthly_quotas",
            "payment_transactions",
            "webhook_events",
            "notifications",
            "device_tokens",
            "otp_challenges",
            "user_sessions",
            "password_reset_tokens",
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

    def test_postgresql_users_email_password_ddl(self):
        pg_dialect = postgresql.dialect()
        users_table = Base.metadata.tables["users"]
        users_ddl = str(CreateTable(users_table).compile(dialect=pg_dialect))
        assert "password_hash VARCHAR(255)" in users_ddl
        assert "email VARCHAR(255)" in users_ddl

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
        test_pg_url = os.environ.get("TEST_POSTGRES_URL") or settings.sync_database_url
        if test_pg_url:
            if test_pg_url.startswith("postgresql://"):
                test_pg_url = test_pg_url.replace("postgresql://", "postgresql+psycopg://", 1)
            elif test_pg_url.startswith("postgres://"):
                test_pg_url = test_pg_url.replace("postgres://", "postgresql+psycopg://", 1)
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

    def test_live_postgres_auth_and_session_persistence(self, pg_engine):
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

            # Create Password Reset Token
            now = datetime.now(timezone.utc)
            reset_record = PasswordResetToken(
                id=uuid.uuid4(),
                user_id=test_user.id,
                token_hash=hash_token(f"test_reset_token_{uuid.uuid4().hex}"),
                expires_at=now + timedelta(minutes=15),
                is_used=False,
            )
            db.add(reset_record)

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

            queried_reset = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == test_user.id).first()
            assert queried_reset is not None
            assert queried_reset.is_used is False

            queried_del = db.query(AccountDeletionRequest).filter(AccountDeletionRequest.user_id == test_user.id).first()
            assert queried_del is not None
            assert queried_del.status == "pending"

        finally:
            db.rollback()
            db.close()

    def test_live_postgres_no_aadhaar_columns_in_physical_schema(self, pg_engine):
        """Read-only physical inspection of information_schema.columns: confirms 0 Aadhaar columns in PostgreSQL."""
        with pg_engine.connect() as conn:
            query = text("""
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
            """)
            rows = conn.execute(query).fetchall()

        assert len(rows) > 0, "No tables/columns found in public schema."
        forbidden = [f"{r[0]}.{r[1]}" for r in rows if "aadhaar" in r[1].lower() or "uidai" in r[1].lower()]
        assert len(forbidden) == 0, f"Forbidden Aadhaar column detected in physical PostgreSQL schema: {forbidden}"


class TestPostgresConcurrencyLive:
    """Rigorous multi-threaded concurrency verification on live PostgreSQL (SEC-04, SEC-05, SEC-06).
    
    Uses concurrent.futures.ThreadPoolExecutor against a real PostgreSQL connection pool.
    Skips cleanly if PostgreSQL daemon is offline.
    """

    @pytest.fixture(scope="class")
    def pg_sessionmaker(self):
        test_pg_url = os.environ.get("TEST_POSTGRES_URL") or settings.sync_database_url
        if test_pg_url:
            if test_pg_url.startswith("postgresql://"):
                test_pg_url = test_pg_url.replace("postgresql://", "postgresql+psycopg://", 1)
            elif test_pg_url.startswith("postgres://"):
                test_pg_url = test_pg_url.replace("postgres://", "postgresql+psycopg://", 1)
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

    def test_concurrent_reminder_claiming_skip_locked_postgres(self, pg_sessionmaker):
        """Verify multiple workers attempting to claim the same reminder using SELECT FOR UPDATE SKIP LOCKED."""
        from concurrent.futures import ThreadPoolExecutor
        from app.models.scheme import Scheme
        from app.models.application import Application, ApplicationReminder
        from app.services.reminder_scheduler import ReminderSchedulerService

        user_id = uuid.uuid4()
        scheme_id = uuid.uuid4()
        app_id = uuid.uuid4()
        rem_id = uuid.uuid4()

        db_init = pg_sessionmaker()
        try:
            test_user = User(
                id=user_id,
                role="citizen",
                mobile_number=f"99{uuid.uuid4().int % 100000000:08d}",
                is_active=True,
            )
            db_init.add(test_user)

            scheme = Scheme(
                id=scheme_id,
                scheme_name=f"Postgres Concurrency Scheme {uuid.uuid4().hex[:6]}",
                description="Scheme description for testing",
                eligibility_summary="Eligibility test summary",
                department="Agriculture",
                category="financial",
                state_applicability="All India",
                official_source_url="https://india.gov.in/scheme",
                official_application_url="https://service.india.gov.in",
                is_active=True,
            )
            db_init.add(scheme)

            app = Application(
                id=app_id,
                user_id=user_id,
                scheme_id=scheme_id,
                application_reference_number=f"APP-PG-{uuid.uuid4().hex[:8]}",
                status="submitted",
            )
            db_init.add(app)

            now = datetime.now(timezone.utc)
            reminder = ApplicationReminder(
                id=rem_id,
                application_id=app_id,
                user_id=user_id,
                title="Postgres Multi-Worker Reminder",
                reminder_date=now - timedelta(hours=1),
                is_completed=False,
                retry_count=0,
            )
            db_init.add(reminder)
            db_init.commit()
        finally:
            db_init.close()

        try:
            def worker_claim(idx):
                db = pg_sessionmaker()
                try:
                    worker_id = f"pg_worker_{idx}_{uuid.uuid4().hex[:4]}"
                    return ReminderSchedulerService.claim_reminder(
                        db=db,
                        reminder_id=rem_id,
                        worker_token=worker_id,
                        now=datetime.now(timezone.utc),
                    )
                finally:
                    db.close()

            with ThreadPoolExecutor(max_workers=5) as executor:
                outcomes = list(executor.map(worker_claim, range(5)))

            # Exactly 1 worker should succeed, 4 should fail/skip
            assert outcomes.count(True) == 1
            assert outcomes.count(False) == 4

            # Verify DB state: reminder is leased to exactly one worker
            db_check = pg_sessionmaker()
            try:
                rem_db = db_check.query(ApplicationReminder).filter(ApplicationReminder.id == rem_id).first()
                assert rem_db.dispatch_token is not None
                assert rem_db.dispatch_lease_until is not None
                assert rem_db.dispatch_lease_until > datetime.now(timezone.utc)
            finally:
                db_check.close()
        finally:
            db_clean = pg_sessionmaker()
            try:
                db_clean.query(ApplicationReminder).filter(ApplicationReminder.id == rem_id).delete(synchronize_session=False)
                db_clean.query(Application).filter(Application.id == app_id).delete(synchronize_session=False)
                db_clean.query(Scheme).filter(Scheme.id == scheme_id).delete(synchronize_session=False)
                db_clean.query(User).filter(User.id == user_id).delete(synchronize_session=False)
                db_clean.commit()
            except Exception:
                db_clean.rollback()
            finally:
                db_clean.close()

    def test_live_postgres_reminder_lease_expiry_and_recovery(self, pg_sessionmaker):
        """Simulate an abandoned lease; verify second worker successfully reclaims after expiration on live PostgreSQL."""
        from app.models.scheme import Scheme
        from app.models.application import Application, ApplicationReminder
        from app.services.reminder_scheduler import ReminderSchedulerService

        user_id = uuid.uuid4()
        scheme_id = uuid.uuid4()
        app_id = uuid.uuid4()
        rem_id = uuid.uuid4()

        db_init = pg_sessionmaker()
        try:
            test_user = User(
                id=user_id,
                role="citizen",
                mobile_number=f"99{uuid.uuid4().int % 100000000:08d}",
                is_active=True,
            )
            db_init.add(test_user)

            scheme = Scheme(
                id=scheme_id,
                scheme_name=f"Postgres Lease Expiry Scheme {uuid.uuid4().hex[:6]}",
                description="Scheme description for testing",
                eligibility_summary="Eligibility test summary",
                department="Education",
                category="scholarship",
                state_applicability="All India",
                official_source_url="https://india.gov.in/scheme",
                official_application_url="https://service.india.gov.in",
                is_active=True,
            )
            db_init.add(scheme)

            app = Application(
                id=app_id,
                user_id=user_id,
                scheme_id=scheme_id,
                application_reference_number=f"APP-LEASE-{uuid.uuid4().hex[:8]}",
                status="submitted",
            )
            db_init.add(app)

            now = datetime.now(timezone.utc)
            # Seed reminder with an expired lease from a crashed worker
            reminder = ApplicationReminder(
                id=rem_id,
                application_id=app_id,
                user_id=user_id,
                title="Crashed Worker Reminder",
                reminder_date=now - timedelta(hours=2),
                is_completed=False,
                dispatch_token="dead_worker_token",
                dispatch_lease_until=now - timedelta(minutes=5),  # expired 5 mins ago
                retry_count=0,
            )
            db_init.add(reminder)
            db_init.commit()
        finally:
            db_init.close()

        try:
            # New worker attempts to claim
            db_claim = pg_sessionmaker()
            try:
                new_worker_token = "alive_worker_token"
                claimed = ReminderSchedulerService.claim_reminder(
                    db=db_claim,
                    reminder_id=rem_id,
                    worker_token=new_worker_token,
                    now=now,
                )
                assert claimed is True
            finally:
                db_claim.close()

            # Check DB reflects new worker ownership
            db_check = pg_sessionmaker()
            try:
                rem_db = db_check.query(ApplicationReminder).filter(ApplicationReminder.id == rem_id).first()
                assert rem_db.dispatch_token == new_worker_token
                assert rem_db.dispatch_lease_until > now
            finally:
                db_check.close()
        finally:
            db_clean = pg_sessionmaker()
            try:
                db_clean.query(ApplicationReminder).filter(ApplicationReminder.id == rem_id).delete(synchronize_session=False)
                db_clean.query(Application).filter(Application.id == app_id).delete(synchronize_session=False)
                db_clean.query(Scheme).filter(Scheme.id == scheme_id).delete(synchronize_session=False)
                db_clean.query(User).filter(User.id == user_id).delete(synchronize_session=False)
                db_clean.commit()
            except Exception:
                db_clean.rollback()
            finally:
                db_clean.close()

    def test_live_postgres_reminder_retry_exhaustion_and_idempotency(self, pg_sessionmaker):
        """Verify reminder retry backoff exhaustion and finalization idempotency on live PostgreSQL."""
        from app.models.scheme import Scheme
        from app.models.application import Application, ApplicationReminder
        from app.services.reminder_scheduler import ReminderSchedulerService

        user_id = uuid.uuid4()
        scheme_id = uuid.uuid4()
        app_id = uuid.uuid4()
        rem_id = uuid.uuid4()

        db_init = pg_sessionmaker()
        try:
            test_user = User(
                id=user_id,
                role="citizen",
                mobile_number=f"99{uuid.uuid4().int % 100000000:08d}",
                is_active=True,
            )
            db_init.add(test_user)

            scheme = Scheme(
                id=scheme_id,
                scheme_name=f"Postgres Retry Scheme {uuid.uuid4().hex[:6]}",
                description="Scheme description for testing",
                eligibility_summary="Eligibility test summary",
                department="Health",
                category="health",
                state_applicability="All India",
                official_source_url="https://india.gov.in/scheme",
                official_application_url="https://service.india.gov.in",
                is_active=True,
            )
            db_init.add(scheme)

            app = Application(
                id=app_id,
                user_id=user_id,
                scheme_id=scheme_id,
                application_reference_number=f"APP-RETRY-{uuid.uuid4().hex[:8]}",
                status="submitted",
            )
            db_init.add(app)

            now = datetime.now(timezone.utc)
            # Reminder with retry_count = 3 (MAX_RETRIES)
            reminder = ApplicationReminder(
                id=rem_id,
                application_id=app_id,
                user_id=user_id,
                title="Max Retries Exhausted",
                reminder_date=now - timedelta(hours=1),
                is_completed=False,
                retry_count=3,
            )
            db_init.add(reminder)
            db_init.commit()
        finally:
            db_init.close()

        try:
            # Claim attempt must fail
            db_claim = pg_sessionmaker()
            try:
                claimed = ReminderSchedulerService.claim_reminder(
                    db=db_claim,
                    reminder_id=rem_id,
                    worker_token="worker_will_fail",
                    now=now,
                )
                assert claimed is False
            finally:
                db_claim.close()
        finally:
            db_clean = pg_sessionmaker()
            try:
                db_clean.query(ApplicationReminder).filter(ApplicationReminder.id == rem_id).delete(synchronize_session=False)
                db_clean.query(Application).filter(Application.id == app_id).delete(synchronize_session=False)
                db_clean.query(Scheme).filter(Scheme.id == scheme_id).delete(synchronize_session=False)
                db_clean.query(User).filter(User.id == user_id).delete(synchronize_session=False)
                db_clean.commit()
            except Exception:
                db_clean.rollback()
            finally:
                db_clean.close()

    def test_live_postgres_concurrent_payment_verification_and_webhook_race(self, pg_sessionmaker):
        """Phase 7: Live PostgreSQL concurrency test verifying race-condition safety between
        PaymentService.verify_and_capture_payment() and PaymentService.process_webhook().
        Multi-worker with_for_update() pessimistic row locking ensures exactly 1 successful activation,
        the other receives an idempotent duplicate/success response, and exactly 1 active subscription is created.
        Strict try...finally ensures all test-created UUID records are cleaned up.
        """
        import hmac
        import hashlib
        import json
        import threading
        from concurrent.futures import ThreadPoolExecutor
        from app.models.payment import PaymentTransaction, WebhookEvent
        from app.models.subscription import Subscription, UserMonthlyQuota
        from app.services.payment_service import PaymentService

        user_id = uuid.uuid4()
        tx_id = uuid.uuid4()
        order_id = f"order_race_{uuid.uuid4().hex[:12]}"
        payment_id = f"pay_race_{uuid.uuid4().hex[:12]}"
        event_id = f"evt_race_{uuid.uuid4().hex[:12]}"

        db_init = pg_sessionmaker()
        try:
            test_user = User(
                id=user_id,
                role="citizen",
                mobile_number=f"99{uuid.uuid4().int % 100000000:08d}",
                is_active=True,
            )
            db_init.add(test_user)

            tx = PaymentTransaction(
                id=tx_id,
                user_id=user_id,
                subscription_id=None,
                razorpay_order_id=order_id,
                razorpay_payment_id=None,
                razorpay_signature=None,
                amount=99.0,
                currency="INR",
                plan_type="premium",
                billing_cycle="monthly",
                payment_status="created",
                payment_method=None,
                idempotency_key=f"idemp_{order_id}",
            )
            db_init.add(tx)
            db_init.commit()
        finally:
            db_init.close()

        # Compute valid HMAC signature for verify_and_capture_payment
        expected_payload = f"{order_id}|{payment_id}".encode("utf-8")
        secret = settings.RAZORPAY_KEY_SECRET.encode("utf-8")
        signature = hmac.new(secret, expected_payload, hashlib.sha256).hexdigest()

        # Build webhook payload and compute valid HMAC signature for process_webhook
        webhook_payload = {
            "event": "payment.captured",
            "event_id": event_id,
            "payload": {
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "order_id": order_id,
                        "status": "captured",
                        "amount": 9900,
                        "currency": "INR",
                        "method": "upi",
                    }
                }
            },
        }
        raw_webhook_body = json.dumps(webhook_payload).encode("utf-8")
        wh_secret = settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8")
        webhook_signature = hmac.new(wh_secret, raw_webhook_body, hashlib.sha256).hexdigest()

        race_barrier = threading.Barrier(2)
        results = {}

        def run_verify():
            db_v = pg_sessionmaker()
            try:
                race_barrier.wait(timeout=10.0)
                res = PaymentService.verify_and_capture_payment(
                    db=db_v,
                    user_id=user_id,
                    order_id=order_id,
                    payment_id=payment_id,
                    signature=signature,
                    payment_method="upi",
                )
                results["verify"] = ("SUCCESS", res)
            except Exception as e:
                results["verify"] = ("ERROR", str(e))
            finally:
                db_v.close()

        def run_webhook():
            db_w = pg_sessionmaker()
            try:
                race_barrier.wait(timeout=10.0)
                res = PaymentService.process_webhook(
                    db=db_w,
                    payload=webhook_payload,
                    raw_body=raw_webhook_body,
                    signature_header=webhook_signature,
                )
                results["webhook"] = ("SUCCESS", res)
            except Exception as e:
                results["webhook"] = ("ERROR", str(e))
            finally:
                db_w.close()

        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                f1 = executor.submit(run_verify)
                f2 = executor.submit(run_webhook)
                f1.result(timeout=15.0)
                f2.result(timeout=15.0)

            # Both threads must complete with SUCCESS status
            assert results["verify"][0] == "SUCCESS", f"Verify failed: {results['verify']}"
            assert results["webhook"][0] == "SUCCESS", f"Webhook failed: {results['webhook']}"

            # Verify idempotency and final database state on live PostgreSQL
            db_verify = pg_sessionmaker()
            try:
                # 1. Transaction status must be 'captured'
                final_tx = db_verify.query(PaymentTransaction).filter(PaymentTransaction.id == tx_id).first()
                assert final_tx is not None
                assert final_tx.payment_status == "captured"
                assert final_tx.razorpay_payment_id == payment_id
                assert final_tx.subscription_id is not None

                # 2. Exactly 1 active subscription must exist for the user
                subs = db_verify.query(Subscription).filter(Subscription.user_id == user_id).all()
                assert len(subs) == 1, f"Expected 1 subscription, found {len(subs)}"
                assert subs[0].status == "active"
                assert subs[0].plan_type == "premium"

                # 3. Monthly quota status resolves to premium allocation (30 docs / 100 AI sessions)
                from app.services.subscription_service import SubscriptionService
                quota_status = SubscriptionService.get_quota_status(db_verify, user_id)
                assert quota_status is not None
                assert quota_status.ai_document_analyses_limit == settings.PREMIUM_MONTHLY_DOC_ANALYSES_LIMIT
                assert quota_status.ai_guidance_sessions_limit == settings.PREMIUM_MONTHLY_AI_GUIDANCE_LIMIT
                assert quota_status.can_analyze_document is True
                assert quota_status.can_request_guidance is True
            finally:
                db_verify.close()

        finally:
            # Deterministic, safe cleanup of all test-created UUID records
            db_cleanup = pg_sessionmaker()
            try:
                db_cleanup.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).delete(synchronize_session=False)
                db_cleanup.query(PaymentTransaction).filter(PaymentTransaction.id == tx_id).delete(synchronize_session=False)
                db_cleanup.query(Subscription).filter(Subscription.user_id == user_id).delete(synchronize_session=False)
                db_cleanup.query(UserMonthlyQuota).filter(UserMonthlyQuota.user_id == user_id).delete(synchronize_session=False)
                db_cleanup.query(User).filter(User.id == user_id).delete(synchronize_session=False)
                db_cleanup.commit()
            except Exception:
                db_cleanup.rollback()
            finally:
                db_cleanup.close()

    def test_live_postgres_transaction_rollback_safety(self, pg_sessionmaker):
        """Verify PostgreSQL transaction rollback cleanly reverts partial uncommitted writes."""
        db = pg_sessionmaker()
        user_id = uuid.uuid4()
        test_user = User(
            id=user_id,
            role="citizen",
            mobile_number=f"99{uuid.uuid4().int % 100000000:08d}",
            is_active=True,
        )
        db.add(test_user)
        db.flush()

        # User is visible in transaction
        assert db.query(User).filter(User.id == user_id).first() is not None

        # Rollback
        db.rollback()

        # User does not exist in DB
        assert db.query(User).filter(User.id == user_id).first() is None
        db.close()

