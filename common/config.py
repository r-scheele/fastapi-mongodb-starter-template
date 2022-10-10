from datetime import timedelta
from typing import Optional

from pydantic import BaseSettings


class Settings(BaseSettings):
    prod: bool = False
    fastapi_log_level: str = "info"
    avatar_data_folder: str = "authentication/avatar/data-dev/avatar-data"
    domain_name: str

    cache_uri: str
    pubsub_uri: str
    mongo_uri: str
    mongo_db: str

    jwt_secret: str = "secret"
    jwt_algorithm: str = "HS256"
    jwt_expiration_seconds: int = timedelta(minutes=15).total_seconds()
    jwt_refresh_expiration_seconds: int = timedelta(weeks=2).total_seconds()

    # Mail
    email_username: str = ""
    email_host: str = ""
    email_password: str = ""
    email_port: int = 587
    email_from: str = ""

    sentry_dsn: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


cfg = Settings()
sentry_config = (
    dict(dsn=cfg.sentry_dsn, traces_sample_rate=1.0) if cfg.sentry_dsn else None
)
