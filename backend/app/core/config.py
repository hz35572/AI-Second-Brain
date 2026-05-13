"""Application configuration using Pydantic BaseSettings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_env_file() -> Path | None:
    """Find .env file in the current or parent directory."""
    current = Path.cwd()
    for path in (current, current.parent):
        env_file = path / ".env"
        if env_file.exists():
            return env_file
    return None


class Settings(BaseSettings):
    """Application settings.

    New code should use the uppercase fields. Lowercase properties are kept as
    compatibility aliases while the backend finishes the config migration.
    """

    model_config = SettingsConfigDict(
        env_file=find_env_file(),
        env_prefix="AISB_",
        env_ignore_empty=True,
        extra="ignore",
    )

    # Project
    PROJECT_NAME: str = "AI-Second-Brain"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "local", "staging", "production"] = "local"
    TIMEZONE: str = "UTC"
    MODELS_CACHE_DIR: Path = Path("./models_cache")
    MEDIA_DIR: Path = Path("./media")
    STORAGE_DIR: Path = Path(".data/storage")
    UPLOAD_TMP_DIR: Path = Path(".data/uploads")
    UPLOAD_CHUNK_SIZE: int = 5 * 1024 * 1024
    MAX_UPLOAD_BYTES: int = 200 * 1024 * 1024
    MAX_UPLOAD_SIZE_MB: int = 200

    # Logfire
    LOGFIRE_TOKEN: str | None = None
    LOGFIRE_SERVICE_NAME: str = "AI-Second-Brain"
    LOGFIRE_ENVIRONMENT: str = "development"

    # Database (PostgreSQL async)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5433
    POSTGRES_USER: str = "aisb"
    POSTGRES_PASSWORD: str = "aisb"
    POSTGRES_DB: str = "aisb"
    DATABASE_URL: str = ""
    DATABASE_URL_SYNC: str = ""
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    @model_validator(mode="after")
    def build_database_urls(self) -> "Settings":
        """Fill database URLs from Postgres parts when not explicitly configured."""
        if not self.DATABASE_URL:
            object.__setattr__(
                self,
                "DATABASE_URL",
                (
                    f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                    f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
                ),
            )
        if not self.DATABASE_URL_SYNC:
            sync_url = self.DATABASE_URL
            sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
            sync_url = sync_url.replace("postgresql+psycopg://", "postgresql+psycopg://")
            object.__setattr__(self, "DATABASE_URL_SYNC", sync_url)
        return self

    # Auth
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    ALGORITHM: str = "HS256"
    API_KEY: str = "change-me-in-production"
    API_KEY_HEADER: str = "X-API-Key"

    # Email verification / SMTP
    SMTP_HOST: str = "smtp.qq.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = "3557298831@qq.com"
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "3557298831@qq.com"
    SMTP_USE_TLS: bool = True
    EMAIL_DEV_MODE: bool = True
    EMAIL_CODE_EXPIRE_MINUTES: int = 10
    EMAIL_CODE_RESEND_INTERVAL_SECONDS: int = 60
    EMAIL_CODE_DAILY_LIMIT: int = 10
    EMAIL_CODE_MAX_ATTEMPTS: int = 5

    # Legacy env names from the previous backend config.
    JWT_SECRET: str | None = None
    JWT_ALGORITHM: str | None = None
    JWT_EXPIRE_MINUTES: int | None = None

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info: ValidationInfo) -> str:
        """Validate SECRET_KEY is secure in production."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        env = info.data.get("ENVIRONMENT", "local") if info.data else "local"
        if v == "change-me-in-production-use-openssl-rand-hex-32" and env == "production":
            raise ValueError("SECRET_KEY must be changed in production")
        return v

    @field_validator("API_KEY")
    @classmethod
    def validate_api_key(cls, v: str, info: ValidationInfo) -> str:
        """Validate API_KEY is set in production."""
        env = info.data.get("ENVIRONMENT", "local") if info.data else "local"
        if v == "change-me-in-production" and env == "production":
            raise ValueError("API_KEY must be changed in production")
        return v

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0
    REDIS_URL: str = ""

    @model_validator(mode="after")
    def build_redis_url(self) -> "Settings":
        """Fill Redis URL from Redis parts when not explicitly configured."""
        if not self.REDIS_URL:
            if self.REDIS_PASSWORD:
                url = f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
            else:
                url = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
            object.__setattr__(self, "REDIS_URL", url)
        return self

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # AI / RAG
    OPENAI_API_KEY: str = ""
    AI_MODEL: str = "gpt-5-mini"
    AI_TEMPERATURE: float = 0.7
    AI_AVAILABLE_MODELS: list[str] = [
        "gpt-5.4",
        "gpt-5.4-mini",
        "gpt-5.4-nano",
        "gpt-5-mini",
        "gpt-5-nano",
        "gpt-5",
        "gpt-5.1",
        "gpt-5.2",
        "o4-mini",
        "o3",
        "o3-mini",
        "gpt-4.1-mini",
        "gpt-4.1",
        "gpt-4.1-nano",
        "gpt-4o",
        "gpt-4o-mini",
    ]
    AI_FRAMEWORK: str = "langgraph"
    LLM_PROVIDER: str = "openai"
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_API_KEY: str | None = None
    LANGCHAIN_PROJECT: str = "AI-Second-Brain"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    RAG_CHUNK_SIZE: int = 512
    RAG_CHUNK_OVERLAP: int = 50
    RAG_DEFAULT_COLLECTION: str = "documents"
    RAG_TOP_K: int = 10
    RAG_CHUNKING_STRATEGY: str = "recursive"
    RAG_HYBRID_SEARCH: bool = False
    RAG_ENABLE_OCR: bool = False
    HF_TOKEN: str = ""
    CROSS_ENCODER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L6-v2"
    RAG_ENABLE_IMAGE_DESCRIPTION: bool = True
    RAG_IMAGE_DESCRIPTION_MODEL: str = ""

    # Optional integrations
    CHANNEL_ENCRYPTION_KEY: str = "change-me-generate-with-openssl-rand-hex-32"
    TELEGRAM_WEBHOOK_BASE_URL: str = ""
    SLACK_SIGNING_SECRET: str = ""
    SLACK_BOT_TOKEN: str = ""
    SLACK_APP_TOKEN: str = ""
    GOOGLE_DRIVE_CREDENTIALS_FILE: str = "credentials/google-drive-sa.json"
    S3_RAG_ENDPOINT: str | None = None
    S3_RAG_ACCESS_KEY: str = ""
    S3_RAG_SECRET_KEY: str = ""
    S3_RAG_BUCKET: str = "ai_agent-rag"
    S3_RAG_REGION: str = "us-east-1"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, v: list[str], info: ValidationInfo) -> list[str]:
        """Reject wildcard CORS in production."""
        env = info.data.get("ENVIRONMENT", "local") if info.data else "local"
        if "*" in v and env == "production":
            raise ValueError("CORS_ORIGINS cannot contain '*' in production")
        return v

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL

    @property
    def debug(self) -> bool:
        return self.DEBUG

    @property
    def storage_dir(self) -> str:
        return str(self.STORAGE_DIR)

    @property
    def upload_tmp_dir(self) -> str:
        return str(self.UPLOAD_TMP_DIR)

    @property
    def upload_chunk_size(self) -> int:
        return self.UPLOAD_CHUNK_SIZE

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_BYTES

    @property
    def cors_allow_origins(self) -> list[str]:
        return self.CORS_ORIGINS

    @property
    def jwt_secret(self) -> str:
        return self.JWT_SECRET or self.SECRET_KEY

    @property
    def jwt_algorithm(self) -> str:
        return self.JWT_ALGORITHM or self.ALGORITHM

    @property
    def jwt_expire_minutes(self) -> int:
        return self.JWT_EXPIRE_MINUTES or self.ACCESS_TOKEN_EXPIRE_MINUTES


settings = Settings()


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return settings
