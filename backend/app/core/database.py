from typing import Generator, Tuple, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from app.core.config import settings
from app.core.logging import logger

# Base class for all SQLAlchemy declarative models
Base = declarative_base()

# Detect SQLite for isolated development / testing
_is_sqlite = settings.sync_database_url.startswith("sqlite")

if _is_sqlite:
    from sqlalchemy.ext.compiler import compiles
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB as PG_JSONB

    @compiles(PG_UUID, "sqlite")
    def compile_uuid_sqlite(type_, compiler, **kw):
        return "CHAR(36)"

    @compiles(PG_JSONB, "sqlite")
    def compile_jsonb_sqlite(type_, compiler, **kw):
        return "JSON"

    engine = create_engine(
        settings.sync_database_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    # Configure SQLAlchemy 2.x engine with Psycopg 3 driver, connection pooling, and connection timeout
    engine = create_engine(
        settings.sync_database_url,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,  # Ensures connections are tested before checkout
        connect_args={"connect_timeout": 3},  # Fast 3-second timeout on unreachable hosts
        echo=False,
    )

# Reusable session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for managing database session lifecycle.
    
    Ensures that a session is opened for each request and safely closed afterwards.
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(f"Database transaction error: {type(exc).__name__}")
        raise
    finally:
        db.close()


def check_database_connection() -> Tuple[bool, Optional[str]]:
    """Test database connectivity by executing a lightweight query (SELECT 1).
    
    Returns:
        (True, None) if reachable, or (False, error_summary) on failure.
        Never leaks passwords or sensitive credentials in the error summary.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, None
    except (OperationalError, Exception) as exc:
        logger.warning(f"Database connection check failed: {type(exc).__name__}")
        return False, "Database server unreachable or credentials rejected."
