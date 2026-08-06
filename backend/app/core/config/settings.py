"""Pydantic Settings — load from environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with safe defaults for local startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AI Customer Support Agent"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_hash_algorithm: str = "argon2"

    database_url: str = "mysql+aiomysql://user:password@localhost:3306/ai_customer_support"
    database_echo: bool = False
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout: int = 30
    database_pool_recycle: int = 1800
    database_connect_timeout: int = 5

    redis_url: str = "redis://localhost:6379/0"

    vector_store_provider: str = "chroma"
    chroma_persist_dir: str = "./.chroma"
    pinecone_api_key: str = ""
    pinecone_index: str = ""

    storage_provider: str = "local"
    local_storage_path: str = "./.storage"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_s3_bucket: str = ""
    aws_region: str = ""

    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    openai_api_key: str = ""

    rate_limit_per_minute: int = 100
    cors_origins: str = "http://localhost:5173"

    # Temporary header-based auth for local/integration tests only.
    # When false (default), X-Super-Admin header cannot elevate privileges.
    auth_header_bypass: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
