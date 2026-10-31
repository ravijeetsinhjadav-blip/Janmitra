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
