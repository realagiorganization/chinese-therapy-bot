# Environment Configuration

The backend reads configuration from environment variables via `AppSettings` (`services/backend/app/core/config.py`). Production deployments must supply the mandatory variables below; optional variables refine behaviour or enable integrations.

## Mandatory Variables
- `APP_ENV`: Logical deployment name (`dev`, `staging`, `prod`) used in logging, metrics, and S3/Key Vault naming.
- `DATABASE_URL`: Async SQLAlchemy connection string for the primary PostgreSQL database (e.g. `postgresql+asyncpg://user:pass@host:5432/db`).
- `JWT_SECRET_KEY`: Symmetric signing key used to mint and validate JWT access/refresh tokens.
- `AZURE_OPENAI_ENDPOINT`: HTTPS endpoint of the Azure OpenAI resource powering chat and summaries.
- `AZURE_OPENAI_API_KEY`: API key providing access to the Azure OpenAI resource.
- `AZURE_OPENAI_DEPLOYMENT`: Deployment name for the primary chat completion model (e.g. `gpt-4o-mini`).
- `AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT`: Deployment name for the embeddings model used by therapist recommendations.
- `AWS_REGION`: AWS region where the S3 buckets and optional Bedrock fallback live (e.g. `ap-northeast-1`).
- `S3_CONVERSATION_LOGS_BUCKET`: S3 bucket storing raw chat transcripts exported by the backend.
- `S3_SUMMARIES_BUCKET`: S3 bucket storing generated daily/weekly conversation summaries.
- `S3_BUCKET_THERAPISTS`: S3 bucket containing normalized therapist profile JSON used by the Data Sync agent.
- `SMS_PROVIDER_API_KEY`: Credential for the SMS provider used to deliver OTP codes (use a sandbox token in non-prod).
- `GOOGLE_OAUTH_CLIENT_ID`: OAuth client ID for Google sign-in flows.
- `GOOGLE_OAUTH_CLIENT_SECRET`: OAuth client secret paired with `GOOGLE_OAUTH_CLIENT_ID`.

## Optional Variables
- `APP_NAME`: Overrides the default service name shown in health endpoints.
- `APP_DEBUG`: Enables FastAPI debug/reload mode (`true`/`false`).
- `API_HOST` / `API_PORT`: Bind address and port for the FastAPI server (defaults `0.0.0.0:8000`).
- `CORS_ALLOW_ORIGINS`: Comma-separated list of allowed origins; defaults to `*` during early development.
- `AZURE_OPENAI_API_VERSION`: API version for Azure OpenAI (defaults to `2024-02-15-preview` when omitted).
- `OPENAI_API_KEY`: Fallback OpenAI API key for local testing when Azure OpenAI is unavailable.
- `OPENAI_EMBEDDING_MODEL`: Model identifier when using OpenAI embeddings fallback (default `text-embedding-3-small`).
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`: Static AWS credentials for environments without role-based access.
- `S3_CONVERSATION_LOGS_PREFIX`: Key prefix for transcript uploads (default `conversations/`).
- `S3_MEDIA_BUCKET`: Optional bucket for audio attachments or rich media served to clients.
- `THERAPIST_DATA_S3_PREFIX`: Overrides the default therapist data prefix (`therapists/`) during ingestion.
- `BEDROCK_REGION`: AWS region hosting the Bedrock fallback model.
- `BEDROCK_MODEL_ID`: Model identifier used when invoking AWS Bedrock as an LLM fallback.
- `SMS_SENDER_ID`: Sender identifier registered with the SMS provider (defaults to provider-specific value when omitted).
- `GOOGLE_OAUTH_REDIRECT_URI`: Redirect URI registered for web/mobile Google OAuth flows.
- `TTS_SERVICE_API_KEY`: Credential for the text-to-speech provider powering voice playback.
- `ASR_SERVICE_API_KEY`: Credential for server-side automatic speech recognition.
- `WECHAT_APP_ID`: Application identifier enabling WeChat voice input integration.
- `FEATURE_FLAGS`: JSON or comma-separated string defining default feature toggles at startup.
- `JWT_ALGORITHM`: Signing algorithm for JWT tokens (default `HS256`).
- `ACCESS_TOKEN_TTL`: Access token lifetime in seconds (default `3600`).
- `REFRESH_TOKEN_TTL`: Refresh token lifetime in seconds (default 30 days).
- `TOKEN_REFRESH_TTL`: Optional override for refresh token grace period on rotation.
- `OTP_EXPIRY_SECONDS`: OTP validity window in seconds (default `300`).
- `OTP_ATTEMPT_LIMIT`: Maximum OTP verification attempts before lockout (default `5`).

### Notes
- When Azure OpenAI variables are omitted, the orchestrator falls back to OpenAI (if configured) and deterministic heuristics for development environments.
- Supplying `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` is unnecessary when running on infrastructure with an attached IAM role (AKS workload identity or EC2 instance profiles).
- Secrets should be stored in Azure Key Vault and AWS Secrets Manager; automation agents hydrate environment variables at runtime using the associated CSI drivers or secret managers.
