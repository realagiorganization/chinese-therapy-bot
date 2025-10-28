from functools import lru_cache
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """Application configuration loaded from environment or .env."""

    app_name: str = Field(default="MindWell API Platform")
    app_env: str = Field(default="dev", alias="APP_ENV")
    debug: bool = Field(default=False, alias="APP_DEBUG")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: ["*"], alias="CORS_ALLOW_ORIGINS"
    )

    openai_api_key: Optional[SecretStr] = Field(default=None, alias="OPENAI_API_KEY")
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")
    aws_region: Optional[str] = Field(default=None, alias="AWS_REGION")
    s3_conversation_logs_bucket: Optional[str] = Field(
        default=None, alias="S3_CONVERSATION_LOGS_BUCKET"
    )
    s3_summaries_bucket: Optional[str] = Field(
        default=None, alias="S3_SUMMARIES_BUCKET"
    )
    s3_media_bucket: Optional[str] = Field(default=None, alias="S3_MEDIA_BUCKET")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> AppSettings:
    """Return cached application settings."""
    return AppSettings()  # type: ignore[call-arg]
