import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
from app.core.database import check_database_connection, _is_sqlite, Base, engine
from app.api.v1.api import api_router


async def _run_reminder_scheduler_loop():
    """Background task that periodically executes due reminder sweeps."""
    logger.info("Application Reminder background scheduler task started.")
    from app.services.reminder_scheduler import ReminderSchedulerService
    from app.core.database import SessionLocal
    while True:
        try:
            await asyncio.sleep(60)  # Periodic 60-second sweep
            with SessionLocal() as db:
                ReminderSchedulerService.process_due_reminders(db)
        except asyncio.CancelledError:
            logger.info("Application Reminder background scheduler task stopped.")
            break
        except Exception as e:
            logger.warning(f"Reminder scheduler background sweep error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for application startup and shutdown."""
    logger.info("JanMitra Assist Backend is starting up...")
    try:
        import app.models
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema and all model tables verified.")
    except Exception as db_err:
        logger.error(f"Primary database connection/init error: {db_err}")
        try:
            from sqlalchemy import create_engine
            import app.core.database as db_mod
            import app.models
            fallback_engine = create_engine("sqlite:////tmp/janmitra.db", connect_args={"check_same_thread": False})
            db_mod.engine = fallback_engine
            db_mod.SessionLocal.configure(bind=fallback_engine)
            Base.metadata.create_all(bind=fallback_engine)
            logger.info("Resilient fallback database (/tmp/janmitra.db) initialized. System operational!")
        except Exception as fb_err:
            logger.error(f"Resilient database fallback encountered error: {fb_err}")

    # Ensure demo schemes and scheme intelligence data are seeded
    try:
        from app.core.database import SessionLocal
        from app.services.scheme_service import SchemeService
        from app.db.seed_scheme_intelligence import seed_scheme_intelligence_data
        with SessionLocal() as db:
            SchemeService.ensure_demo_schemes_seeded(db)
            seed_scheme_intelligence_data(db)
            logger.info("Demo schemes and scheme intelligence metadata verified.")
    except Exception as e:
        logger.warning(f"Scheme & intelligence auto-seed verification skipped: {e}")

    # One-time administrator bootstrap if configured and no admin exists
    if settings.INITIAL_ADMIN_EMAIL and settings.INITIAL_ADMIN_PASSWORD:
        try:
            from app.core.database import SessionLocal
            from app.models.user import User
            from app.cli.admin_create import provision_admin
            with SessionLocal() as db:
                if db.query(User).filter(User.role == "admin").count() == 0:
                    provision_admin(settings.INITIAL_ADMIN_EMAIL, settings.INITIAL_ADMIN_PASSWORD)
                    logger.info("Initial administrator provisioned via settings bootstrap.")
        except Exception as e:
            logger.warning(f"Initial administrator bootstrap check skipped or failed: {e}")

    # Launch background reminder scheduler task
    scheduler_task = asyncio.create_task(_run_reminder_scheduler_loop())

    yield

    # Clean shutdown of scheduler task
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass

    logger.info("JanMitra Assist Backend is shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for JanMitra Assist - AI-Powered Government Service Eligibility and Document Intelligence System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware setup - permits explicit origins and any local dev port (localhost / 127.0.0.1)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach API v1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
def read_root():
    """Root endpoint welcoming clients."""
    return {
        "project": "JanMitra Assist",
        "description": "AI-Powered Government Service Eligibility and Document Intelligence System",
        "status": "online",
        "health_check": "/health",
        "database_health": "/health/database",
        "documentation": "/docs",
    }


@app.get("/health", tags=["System"])
def health_check():
    """General backend health-check endpoint indicating that the FastAPI service is running."""
    logger.info("Health check endpoint accessed")
    return {
        "status": "healthy",
        "message": "JanMitra Assist backend is running successfully",
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
    }


@app.get("/health/database", tags=["System"])
@app.get("/database/health", tags=["System"], include_in_schema=False)
def database_health_check():
    """PostgreSQL database connectivity health check.
    
    Verifies that the database server is reachable and responsive by executing
    a lightweight query. Returns HTTP 503 if the database is disconnected.
    Never exposes passwords or sensitive connection parameters.
    """
    logger.info("Database health check accessed")
    is_connected, error_msg = check_database_connection()

    db_type = "SQLite" if _is_sqlite else "PostgreSQL"
    driver_name = "sqlite3" if _is_sqlite else "psycopg3"

    if is_connected:
        return {
            "status": "healthy",
            "database": "connected",
            "database_type": db_type,
            "driver": driver_name,
            "environment": settings.ENVIRONMENT,
        }

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "unhealthy",
            "database": "disconnected",
            "database_type": db_type,
            "driver": driver_name,
            "error": error_msg or "Database connection failed",
            "environment": settings.ENVIRONMENT,
        },
    )
