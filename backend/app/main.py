from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
from app.core.database import check_database_connection
from app.api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for application startup and shutdown."""
    logger.info("JanMitra Assist Backend is starting up...")
    yield
    logger.info("JanMitra Assist Backend is shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for JanMitra Assist - AI-Powered Government Service Eligibility and Document Intelligence System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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
def database_health_check():
    """PostgreSQL database connectivity health check.
    
    Verifies that the database server is reachable and responsive by executing
    a lightweight query. Returns HTTP 503 if the database is disconnected.
    Never exposes passwords or sensitive connection parameters.
    """
    logger.info("Database health check accessed")
    is_connected, error_msg = check_database_connection()

    if is_connected:
        return {
            "status": "healthy",
            "database": "connected",
            "database_type": "PostgreSQL",
            "driver": "psycopg3",
            "environment": settings.ENVIRONMENT,
        }

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "unhealthy",
            "database": "disconnected",
            "database_type": "PostgreSQL",
            "driver": "psycopg3",
            "error": error_msg or "Database connection failed",
            "environment": settings.ENVIRONMENT,
        },
    )
