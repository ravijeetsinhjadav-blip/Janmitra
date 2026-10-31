from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    PROJECT_NAME: str = "JanMitra Assist API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    HOST: str = "127.0.0.1"
    PORT: int = 8000

    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080"
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

    # OTP Authentication Settings (Phase 3)
    OTP_LENGTH: int = 6
    OTP_EXPIRE_SECONDS: int = 300  # 5 minutes
    OTP_MAX_ATTEMPTS: int = 3
    OTP_RESEND_COOLDOWN_SECONDS: int = 60
    OTP_DEV_MODE: bool = True  # Returns development OTP for local testing
    SMS_PROVIDER: str = "development"  # Options: 'development', 'production_sms'

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

    @property
    def allowed_extensions(self) -> List[str]:
        return [ext.strip().lower().lstrip(".") for ext in self.ALLOWED_DOCUMENT_EXTENSIONS.split(",") if ext.strip()]

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

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
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
