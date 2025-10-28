# Environment Configuration

## Mandatory Variables
- `APP_ENV`: Deployment environment identifier (`development`, `staging`, `production`) used for environment-specific toggles.
- `API_PORT`: Port where the backend HTTP server listens (e.g., `8000`).
- `DATABASE_URL`: Connection string for the primary relational database storing users, therapists, sessions, and reports.
- `CACHE_URL`: Connection string for the distributed cache (Redis) used for session tokens and rate limiting.
- `JWT_SECRET`: Signing secret for issuing and validating authentication tokens.
- `AZURE_OPENAI_ENDPOINT`: HTTPS endpoint of the Azure OpenAI resource powering chatbot responses.
- `AZURE_OPENAI_API_KEY`: API key granting access to the Azure OpenAI resource.
- `AZURE_OPENAI_DEPLOYMENT`: Deployment name of the primary chat completion model on Azure.
- `AZURE_OPENAI_API_VERSION`: Version string required for Azure OpenAI REST API requests.
- `AWS_REGION`: Region identifier for AWS resources (S3, Bedrock fallback).
- `AWS_ACCESS_KEY_ID`: IAM access key with permissions for S3 and Bedrock.
- `AWS_SECRET_ACCESS_KEY`: Secret associated with the IAM access key.
- `S3_BUCKET_CONVERSATIONS`: S3 bucket name used to store raw chat transcripts.
- `S3_BUCKET_SUMMARIES`: S3 bucket name used to store generated daily and weekly summaries.
- `SMS_PROVIDER_API_KEY`: Credential for the SMS gateway used during login verification.
- `GOOGLE_OAUTH_CLIENT_ID`: Client ID for Google OAuth login.
- `GOOGLE_OAUTH_CLIENT_SECRET`: Client secret for Google OAuth login.

## Optional Variables
- `LOG_LEVEL`: Overrides default logging verbosity (`info`, `debug`, `warn`, `error`).
- `CORS_ALLOWED_ORIGINS`: Comma-separated list of origins permitted to access the API.
- `TOKEN_REFRESH_TTL`: Duration (in seconds) for refresh token validity window.
- `AZURE_KEY_VAULT_NAME`: Name of the Azure Key Vault storing secrets when externalized.
- `BEDROCK_REGION`: AWS region hosting Bedrock for fallback model inference.
- `BEDROCK_MODEL_ID`: Identifier of the Bedrock model used when Azure OpenAI is unavailable.
- `TTS_SERVICE_API_KEY`: Credential for text-to-speech provider used in voice playback.
- `ASR_SERVICE_API_KEY`: Credential for speech-to-text service supporting voice input.
- `WECHAT_APP_ID`: Application ID for WeChat voice integration (if enabled).
- `THERAPIST_DATA_S3_PREFIX`: Optional S3 key prefix for therapist data imports.
- `FEATURE_FLAGS`: JSON or comma-separated toggles enabling experimental functionality.
