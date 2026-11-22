"""Configuración por entorno (12-factor) de la API."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "development"
    app_base_url: str = "http://localhost:8090"

    jwt_secret: str = "change-me-in-production"
    jwt_access_ttl_min: int = 15
    jwt_refresh_ttl_days: int = 30

    database_url: str = "postgresql+psycopg://issitek:issitek@localhost:5433/issitek_language"
    cors_origins: str = "http://localhost:5180,http://localhost:8090"

    minio_endpoint: str = "localhost:9100"
    # Endpoint que se usa en las URLs firmadas que ve el navegador. En Compose
    # apunta al proxy nginx (/s3) porque `storage:9000` no es resoluble fuera.
    minio_public_endpoint: str | None = None
    minio_access_key: str = "issitek"
    minio_secret_key: str = "change-me"
    minio_secure: bool = False
    minio_bucket_reference: str = "reference-audio"
    minio_bucket_recordings: str = "student-recordings"
    minio_presign_ttl_s: int = 300

    tts_local_url: str = "http://127.0.0.1:9082"
    tts_provider: str = "kokoro"  # kokoro | fake
    tts_default_voice: str = "af_heart"

    pronunciation_eval_enabled: bool = False
    pronunciation_eval_engine: str = "fake"

    recording_retention_days: int = 30
    recording_max_seconds: int = 15
    recording_max_bytes: int = 5_000_000

    # Worker de retención (F1). En producción puede ejecutarse cada hora.
    worker_interval_seconds: int = 3600
    worker_run_once: bool = False
    worker_heartbeat_path: str = "/tmp/issitek-worker-heartbeat"
    worker_batch_size: int = 500

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def recording_retention_seconds(self) -> int:
        return self.recording_retention_days * 24 * 3600


@lru_cache
def get_settings() -> Settings:
    return Settings()
