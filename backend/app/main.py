from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
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
        "documentation": "/docs"
    }


@app.get("/health", tags=["System"])
def health_check():
    """Health-check endpoint indicating that the backend is running."""
    logger.info("Health check endpoint accessed")
    return {
        "status": "healthy",
        "message": "JanMitra Assist backend is running successfully",
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0"
    }
