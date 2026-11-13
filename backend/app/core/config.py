"""Environment-based configuration. Never hardcode secrets."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="LEARNDNA_", extra="ignore")

    env: str = "development"
    database_url: str = "postgresql+psycopg://learndna:learndna@localhost:5432/learndna"
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret: str = "CHANGE_ME_DEV_ONLY_insecure_default_key_000"  # must be overridden outside development
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = 60

    # Background processing: "celery" in prod, "inline" for dev/test without Redis
    task_backend: str = "inline"

    # Storage
    storage_backend: str = "local"  # local | s3
    local_storage_dir: str = "./var/uploads"
    max_upload_mb: int = 40

    # AI providers
    vision_provider: str = "mock"  # mock | openai_compatible
    llm_provider: str = "mock"
    openai_base_url: str | None = None
    openai_api_key: str | None = None
    openai_vision_model: str | None = None
    openai_text_model: str | None = None

    # Malware scanning
    malware_scanner: str = "none"  # none | clamav
    clamav_host: str = "localhost"
    clamav_port: int = 3310

    # Error reasoning thresholds
    ocr_min_confidence: float = 0.60
    review_confidence_threshold: float = 0.70

    def validate_for_runtime(self) -> None:
        if self.env != "development" and self.jwt_secret.startswith("CHANGE_ME"):
            raise RuntimeError("LEARNDNA_JWT_SECRET must be set outside development")


@lru_cache
def get_settings() -> Settings:
    return Settings()
