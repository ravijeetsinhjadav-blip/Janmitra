import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator


class Settings(BaseSettings):
    PROJECT_NAME: str = "JanMitra Assist API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    HOST: str = "127.0.0.1"
    PORT: int = 8000

    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080"
    LOG_LEVEL: str = "INFO"

    # PostgreSQL Database Settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "janmitra_db"
    DATABASE_URL: Optional[str] = None

    # Connection pool configuration
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # JWT Authentication Settings (Phase 3)
    JWT_SECRET_KEY: str = "janmitra_insecure_default_dev_secret_change_in_production_32bytes"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Initial Administrator Bootstrap (Optional, for one-time initialization)
    INITIAL_ADMIN_EMAIL: Optional[str] = None
    INITIAL_ADMIN_PASSWORD: Optional[str] = None

    # SMTP Email & Password Recovery Settings (Phase 11)
    SMTP_HOST: Optional[str] = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "noreply@janmitra.gov.in"
    SMTP_FROM_NAME: str = "JanMitra Assist"
    SMTP_USE_TLS: bool = False
    SMTP_USE_SSL: bool = False
    FRONTEND_BASE_URL: str = "http://localhost:8080"
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 15

    # Rate Limiting & Brute Force Protection Settings (Phase 11)
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 300  # 5 minutes
    PASSWORD_RESET_RATE_LIMIT_MAX_ATTEMPTS: int = 3
    PASSWORD_RESET_RATE_LIMIT_WINDOW_SECONDS: int = 900  # 15 minutes

    # User Account Deletion & Retention Settings (Phase 3)
    ACCOUNT_DELETION_RETENTION_DAYS: int = 30  # Configurable grace/statutory retention period

    # Document Storage Settings (Phase 5)
    DOCUMENT_STORAGE_PATH: str = "storage/documents"
    MAX_DOCUMENT_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_DOCUMENT_EXTENSIONS: str = "pdf,jpg,jpeg,png"

    # OCR Pipeline Settings (Phase 5)
    OCR_PROVIDER: str = "google_cloud_vision"  # 'google_cloud_vision' or 'mock'
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    OCR_CONFIDENCE_THRESHOLD: float = 0.70

    # AI Advisory & LLM Provider Settings (Phase 6)
    AI_PROVIDER: str = "gemini"  # Options: 'gemini', 'openai_compatible', 'mock'
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.8-flash"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    AI_REQUEST_TIMEOUT_SECONDS: int = 30
    AI_MAX_RETRIES: int = 2
    RAG_TOP_K: int = 3
    DEFAULT_ADVISORY_LANGUAGE: str = "en"  # Supported: 'en', 'hi', 'gu'

    # Razorpay Payment & Subscription Settings (Phase 7.2)
    RAZORPAY_KEY_ID: str = "rzp_test_janmitra_dev_key"
    RAZORPAY_KEY_SECRET: str = "janmitra_razorpay_secret_dev_32char"
    RAZORPAY_WEBHOOK_SECRET: str = "janmitra_webhook_secret_dev_32char"
    RAZORPAY_CURRENCY: str = "INR"
    RAZORPAY_DEV_MODE: bool = True  # Allows deterministic mock order/verification in dev/test

    # Subscription Quota Limits
    FREE_MONTHLY_DOC_ANALYSES_LIMIT: int = 3
    PREMIUM_MONTHLY_DOC_ANALYSES_LIMIT: int = 30
    FREE_MONTHLY_AI_GUIDANCE_LIMIT: int = 5
    # Proposed fair-use safety limit pending Project Owner commercial confirmation. Configurable via .env.
    PREMIUM_MONTHLY_AI_GUIDANCE_LIMIT: int = 100

    @property
    def allowed_extensions(self) -> List[str]:
        return [ext.strip().lower().lstrip(".") for ext in self.ALLOWED_DOCUMENT_EXTENSIONS.split(",") if ext.strip()]

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            # 1. Enforce strong non-default JWT secret
            if (
                not self.JWT_SECRET_KEY
                or self.JWT_SECRET_KEY == "janmitra_insecure_default_dev_secret_change_in_production_32bytes"
                or "change_me" in self.JWT_SECRET_KEY.lower()
                or len(self.JWT_SECRET_KEY) < 32
            ):
                raise ValueError("CRITICAL SECURITY ERROR: Strong, non-default JWT_SECRET_KEY (>= 32 chars) required in production.")

            # 2. Enforce exact production CORS origins (no localhost)
            for origin in self.cors_origins:
                if "localhost" in origin.lower() or "127.0.0.1" in origin:
                    raise ValueError(f"CRITICAL SECURITY ERROR: Localhost origin '{origin}' is strictly prohibited in production ALLOWED_ORIGINS.")

            # 3. Enforce valid Razorpay credentials
            if self.RAZORPAY_DEV_MODE:
                raise ValueError("CRITICAL SECURITY ERROR: RAZORPAY_DEV_MODE cannot be enabled in production.")
            if (
                not self.RAZORPAY_KEY_ID
                or self.RAZORPAY_KEY_ID == "rzp_test_janmitra_dev_key"
                or "placeholder" in self.RAZORPAY_KEY_ID.lower()
            ):
                raise ValueError("CRITICAL SECURITY ERROR: Live RAZORPAY_KEY_ID required in production.")
            if (
                not self.RAZORPAY_KEY_SECRET
                or "dev_32char" in self.RAZORPAY_KEY_SECRET
                or "placeholder" in self.RAZORPAY_KEY_SECRET.lower()
            ):
                raise ValueError("CRITICAL SECURITY ERROR: Live RAZORPAY_KEY_SECRET required in production.")
            if (
                not self.RAZORPAY_WEBHOOK_SECRET
                or "dev_32char" in self.RAZORPAY_WEBHOOK_SECRET
                or "placeholder" in self.RAZORPAY_WEBHOOK_SECRET.lower()
            ):
                raise ValueError("CRITICAL SECURITY ERROR: Live RAZORPAY_WEBHOOK_SECRET required in production.")

            # 4. Enforce PostgreSQL in production (no SQLite fallback permitted)
            if self.sync_database_url.startswith("sqlite"):
                raise ValueError("CRITICAL ARCHITECTURE ERROR: SQLite is strictly prohibited in production. PostgreSQL 16 is required.")

            # 5. Enforce AI Provider credentials in production (no mock permitted)
            if self.AI_PROVIDER.lower() == "mock":
                raise ValueError("CRITICAL SECURITY ERROR: AI_PROVIDER='mock' is strictly prohibited in production. Live Gemini configuration required.")
            if self.AI_PROVIDER.lower() == "gemini":
                if (
                    not self.GEMINI_API_KEY
                    or "your_" in self.GEMINI_API_KEY.lower()
                    or "placeholder" in self.GEMINI_API_KEY.lower()
                    or len(self.GEMINI_API_KEY.strip()) < 10
                ):
                    raise ValueError("CRITICAL SECURITY ERROR: Valid GEMINI_API_KEY required in production when AI_PROVIDER='gemini'.")

            # 6. Enforce OCR Provider credentials in production (no mock permitted)
            if self.OCR_PROVIDER.lower() == "mock":
                raise ValueError("CRITICAL SECURITY ERROR: OCR_PROVIDER='mock' is strictly prohibited in production. Google Cloud Vision configuration required.")
            if self.OCR_PROVIDER.lower() == "google_cloud_vision":
                if not self.GOOGLE_APPLICATION_CREDENTIALS or not os.path.exists(self.GOOGLE_APPLICATION_CREDENTIALS):
                    raise ValueError("CRITICAL SECURITY ERROR: Valid GOOGLE_APPLICATION_CREDENTIALS file path required in production when OCR_PROVIDER='google_cloud_vision'.")
        return self

    @property
    def sync_database_url(self) -> str:
        """Return the PostgreSQL connection string formatted for SQLAlchemy with Psycopg 3."""
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+psycopg://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+psycopg://", 1)
            return url
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
