from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    database_url: str = "postgresql://admin:secret@localhost:5432/tunel"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    rate_limit_per_hour: int = 10
    scan_timeout_seconds: int = 300
    wmn_concurrency: int = 40
    wmn_request_timeout: float = 10.0
    wmn_include_nsfw: bool = False
    sherlock_timeout: int = 180
    http_retries: int = 2
    engine_timeout_seconds: int = 240

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
