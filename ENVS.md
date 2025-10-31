# Environment Configuration

## Mandatory Variables
- `APP_ENV`: Deployment environment identifier (`development`, `staging`, `production`) used for environment-specific toggles.
- `API_HOST`: Interface the FastAPI service binds to (default `0.0.0.0`).
- `API_PORT`: Port where the backend HTTP server listens (e.g., `8000`).
- `CORS_ALLOW_ORIGINS`: Comma-separated list of origins allowed to access the API.
- `DATABASE_URL`: Async SQLAlchemy/Postgres connection string storing users, therapists, sessions, and summaries.
- `JWT_SECRET_KEY`: Symmetric signing key used to mint and validate JWT access tokens.
- `AZURE_OPENAI_ENDPOINT`: HTTPS endpoint of the Azure OpenAI resource powering chatbot responses.
- `AZURE_OPENAI_API_KEY`: API key granting access to the Azure OpenAI resource.
- `AZURE_OPENAI_DEPLOYMENT`: Deployment name of the primary chat completion model on Azure.
- `AZURE_OPENAI_API_VERSION`: Version string required for Azure OpenAI REST API requests.
- `AWS_REGION`: Region identifier for AWS resources (S3, Bedrock fallback).
- `S3_CONVERSATION_LOGS_BUCKET`: S3 bucket name used to store raw chat transcripts.
- `S3_SUMMARIES_BUCKET`: S3 bucket used to store generated daily and weekly summaries.
- `SMS_PROVIDER_API_KEY`: Credential for the SMS gateway used during login verification (set to a placeholder when using the console debug provider).
- `GOOGLE_OAUTH_CLIENT_ID`: Client ID for Google OAuth login.
- `GOOGLE_OAUTH_CLIENT_SECRET`: Client secret for Google OAuth login.

## Optional Variables
- `APP_DEBUG`: Enables debug mode (auto-reload, verbose logging) when set to `true`.
- `JWT_ALGORITHM`: JWT signing algorithm (defaults to `HS256`).
- `ACCESS_TOKEN_TTL`: Access token lifetime in seconds (defaults to `3600`).
- `REFRESH_TOKEN_TTL`: Refresh token lifetime in seconds (defaults to 30 days).
- `OTP_EXPIRY_SECONDS`: Seconds before SMS login challenges expire (default `300`).
- `OTP_ATTEMPT_LIMIT`: Maximum OTP verification attempts before lockout (default `5`).
- `OPENAI_API_KEY`: Generic OpenAI key for local experimentation outside Azure.
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`: IAM credentials for Bedrock or S3 in environments without instance profiles.
- `S3_CONVERSATION_LOGS_PREFIX`: Key prefix for transcript uploads (default `conversations/`).
- `S3_BUCKET_THERAPISTS`: Bucket containing normalized therapist profile JSON files consumed by the admin import endpoint.
- `S3_MEDIA_BUCKET`: Bucket for storing rich media assets (audio snippets, attachments).
- `THERAPIST_DATA_S3_PREFIX`: Optional S3 key prefix for therapist data imports.
- `BEDROCK_REGION`: AWS region hosting Bedrock fallback model inference.
- `BEDROCK_MODEL_ID`: Identifier of the Bedrock model used when Azure OpenAI is unavailable.
- `SMS_SENDER_ID`: Sender identifier registered with the SMS provider.
- `GOOGLE_OAUTH_REDIRECT_URI`: Redirect URI registered with Google OAuth for web/mobile clients.
- `TTS_SERVICE_API_KEY`: Credential for text-to-speech provider used in voice playback.
- `ASR_SERVICE_API_KEY`: Credential for speech-to-text service supporting voice input.
- `WECHAT_APP_ID`: Application ID for WeChat voice integration (if enabled).
- `FEATURE_FLAGS`: JSON or comma-separated toggles enabling experimental functionality.
- `AZURE_KEY_VAULT_NAME`: Name of the Azure Key Vault storing secrets when externalized.
- `LOG_LEVEL`: Overrides default logging verbosity (`info`, `debug`, `warn`, `error`).
- `AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT`: Deployment identifier for the Azure OpenAI embeddings model powering the recommendation index.
- `OPENAI_EMBEDDING_MODEL`: Model identifier to use when falling back to OpenAI embeddings (defaults to `text-embedding-3-small`).
