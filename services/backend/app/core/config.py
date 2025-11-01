from functools import lru_cache
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application configuration loaded from environment or .env."""

    app_name: str = Field(default="MindWell API Platform")
    app_env: str = Field(default="dev", alias="APP_ENV")
    debug: bool = Field(default=False, alias="APP_DEBUG")
    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: ["*"], alias="CORS_ALLOW_ORIGINS"
    )

    jwt_secret_key: Optional[SecretStr] = Field(default=None, alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_ttl: int = Field(default=3600, alias="ACCESS_TOKEN_TTL")
    refresh_token_ttl: int = Field(default=60 * 60 * 24 * 30, alias="REFRESH_TOKEN_TTL")
    otp_expiry_seconds: int = Field(default=300, alias="OTP_EXPIRY_SECONDS")
    otp_attempt_limit: int = Field(default=5, alias="OTP_ATTEMPT_LIMIT")

    openai_api_key: Optional[SecretStr] = Field(default=None, alias="OPENAI_API_KEY")
    azure_openai_endpoint: Optional[str] = Field(default=None, alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: Optional[SecretStr] = Field(default=None, alias="AZURE_OPENAI_API_KEY")
    azure_openai_deployment: Optional[str] = Field(default=None, alias="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_api_version: Optional[str] = Field(default=None, alias="AZURE_OPENAI_API_VERSION")
    azure_openai_embeddings_deployment: Optional[str] = Field(
        default=None, alias="AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT"
    )
    azure_speech_key: Optional[SecretStr] = Field(default=None, alias="AZURE_SPEECH_KEY")
    azure_speech_region: Optional[str] = Field(default=None, alias="AZURE_SPEECH_REGION")
    azure_speech_endpoint: Optional[str] = Field(default=None, alias="AZURE_SPEECH_ENDPOINT")
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")
    aws_region: Optional[str] = Field(default=None, alias="AWS_REGION")
    aws_access_key_id: Optional[SecretStr] = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[SecretStr] = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    s3_conversation_logs_bucket: Optional[str] = Field(
        default=None, alias="S3_CONVERSATION_LOGS_BUCKET"
    )
    s3_summaries_bucket: Optional[str] = Field(
        default=None, alias="S3_SUMMARIES_BUCKET"
    )
    s3_therapists_bucket: Optional[str] = Field(
        default=None, alias="S3_BUCKET_THERAPISTS"
    )
    s3_conversation_logs_prefix: Optional[str] = Field(
        default="conversations/", alias="S3_CONVERSATION_LOGS_PREFIX"
    )
    s3_media_bucket: Optional[str] = Field(default=None, alias="S3_MEDIA_BUCKET")
    therapist_data_s3_prefix: Optional[str] = Field(
        default=None, alias="THERAPIST_DATA_S3_PREFIX"
    )
    conversation_logs_retention_months: int = Field(
        default=18, alias="CONVERSATION_LOGS_RETENTION_MONTHS"
    )
    conversation_logs_delete_months: int = Field(
        default=24, alias="CONVERSATION_LOGS_DELETE_MONTHS"
    )
    daily_summary_retention_months: int = Field(
        default=24, alias="DAILY_SUMMARY_RETENTION_MONTHS"
    )
    bedrock_region: Optional[str] = Field(default=None, alias="BEDROCK_REGION")
    bedrock_model_id: Optional[str] = Field(default=None, alias="BEDROCK_MODEL_ID")
    sms_provider_api_key: Optional[SecretStr] = Field(
        default=None, alias="SMS_PROVIDER_API_KEY"
    )
    sms_sender_id: Optional[str] = Field(default=None, alias="SMS_SENDER_ID")
    google_oauth_client_id: Optional[str] = Field(
        default=None, alias="GOOGLE_OAUTH_CLIENT_ID"
    )
    google_oauth_client_secret: Optional[SecretStr] = Field(
        default=None, alias="GOOGLE_OAUTH_CLIENT_SECRET"
    )
    google_oauth_redirect_uri: Optional[str] = Field(
        default=None, alias="GOOGLE_OAUTH_REDIRECT_URI"
    )
    tts_service_api_key: Optional[SecretStr] = Field(
        default=None, alias="TTS_SERVICE_API_KEY"
    )
    asr_service_api_key: Optional[SecretStr] = Field(
        default=None, alias="ASR_SERVICE_API_KEY"
    )
    wechat_app_id: Optional[str] = Field(default=None, alias="WECHAT_APP_ID")
    token_refresh_ttl: Optional[int] = Field(default=None, alias="TOKEN_REFRESH_TTL")
    feature_flags: Optional[str] = Field(default=None, alias="FEATURE_FLAGS")
    openai_embedding_model: Optional[str] = Field(default=None, alias="OPENAI_EMBEDDING_MODEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> AppSettings:
    """Return cached application settings."""
    return AppSettings()  # type: ignore[call-arg]
