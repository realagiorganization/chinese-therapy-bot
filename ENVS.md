# Environment Configuration

The backend reads configuration from environment variables via `AppSettings` (`services/backend/app/core/config.py`). Production deployments must supply the mandatory variables below; optional variables refine behaviour or enable integrations.

## Mandatory Variables
### Backend Services
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

### Frontend Web Client
- `VITE_API_BASE_URL`: Fully qualified base URL of the deployed backend (e.g. `https://api.mindwell.cn`). Defaults to `http://localhost:8000` for local development but must be set for production builds.

### Mobile (React Native) Clients
- `EXPO_PUBLIC_API_BASE_URL`: Mirrors `VITE_API_BASE_URL` for Expo builds; injected via Expo config plugin.
- `EXPO_PUBLIC_SPEECH_REGION`: Region hint for speech features (populated from Key Vault during build automation).

## Optional Variables
### Backend Services
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
- `AZURE_SPEECH_KEY`: Subscription key for Azure Cognitive Services Speech, enabling server-side audio transcription.
- `AZURE_SPEECH_REGION`: Azure region hosting the Speech resource (e.g. `eastasia`) used by the ASR integration.
- `AZURE_SPEECH_ENDPOINT`: Optional override for the Speech-to-Text endpoint when using a private link or custom domain.
- `TTS_SERVICE_API_KEY`: Credential for the text-to-speech provider powering voice playback.
- `ASR_SERVICE_API_KEY`: Credential for server-side automatic speech recognition.
- `APP_INSIGHTS_APP_ID`: Azure Application Insights application identifier used by the Monitoring Agent to query metrics.
- `APP_INSIGHTS_API_KEY`: API key granting query access to Application Insights for observability checks.
- `WECHAT_APP_ID`: Application identifier enabling WeChat voice input integration.
- `FEATURE_FLAGS`: JSON or comma-separated string defining default feature toggles at startup.
- `JWT_ALGORITHM`: Signing algorithm for JWT tokens (default `HS256`).
- `ACCESS_TOKEN_TTL`: Access token lifetime in seconds (default `3600`).
- `REFRESH_TOKEN_TTL`: Refresh token lifetime in seconds (default 30 days).
- `TOKEN_REFRESH_TTL`: Optional override for refresh token grace period on rotation.
- `OTP_EXPIRY_SECONDS`: OTP validity window in seconds (default `300`).
- `OTP_ATTEMPT_LIMIT`: Maximum OTP verification attempts before lockout (default `5`).
- `MONITORING_LATENCY_THRESHOLD_MS`: 95th percentile latency guardrail in milliseconds before the Monitoring Agent raises an alert (default `1200`).
- `MONITORING_ERROR_RATE_THRESHOLD`: Maximum acceptable application error rate expressed as a decimal (default `0.05` for 5%).
- `MONITORING_COST_THRESHOLD_USD`: Daily cloud spend threshold in USD that triggers alerts when exceeded (default `500`).
- `MONITORING_COST_LOOKBACK_DAYS`: Number of trailing days the Monitoring Agent evaluates when computing spend (default `1`).
- `ALERT_WEBHOOK_URL`: Optional HTTPS webhook endpoint (e.g. Slack, Teams) that receives Monitoring Agent alert payloads.
- `ALERT_CHANNEL`: Optional channel or room override supplied with alert webhook payloads.

### Notes
- When Azure OpenAI variables are omitted, the orchestrator falls back to OpenAI (if configured) and deterministic heuristics for development environments.
- Supplying `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` is unnecessary when running on infrastructure with an attached IAM role (AKS workload identity or EC2 instance profiles).
- Secrets should be stored in Azure Key Vault and AWS Secrets Manager; automation agents hydrate environment variables at runtime using the associated CSI drivers or secret managers.

## Source of Truth & Rotation Overview
The table below captures the authoritative location, owning team, and rotation cadence for high-sensitivity configuration. Environment-specific manifests live under `infra/environments/`; secrets are never committed to the repository.

| Variable | Required Environments | Source of Truth | Rotation Owner | Rotation Cadence | Automation Hooks |
| --- | --- | --- | --- | --- | --- |
| `JWT_SECRET_KEY` | dev / staging / prod | Azure Key Vault `kv-mindwell-<env>` secret `jwt-secret-key` | Platform Engineering | Semi-annual or after security incident | Rotated via GitHub Actions workflow `rotate-jwt-secret.yml` invoking Key Vault + Secrets Manager replication |
| `DATABASE_URL` | dev / staging / prod | Azure Key Vault `kv-mindwell-<env>` secret `postgres-connection-string` | Data Platform | After credential rotation (quarterly) | Terraform outputs feed Azure DevOps pipeline that updates Key Vault and issues Postgres credential rotation using `az postgres flexible-server` |
| `AZURE_OPENAI_API_KEY` | staging / prod | Azure Key Vault secret `azure-openai-api-key` | Applied AI Team | 90 days | Summary Scheduler Agent listens to rotation event grid topic and refreshes cache |
| `AZURE_OPENAI_DEPLOYMENT` | staging / prod | Terraform variable `azure_openai_deployment` | Applied AI Team | On model upgrade | Terraform plan gate requires AI signoff |
| `AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT` | staging / prod | Terraform variable `azure_openai_embeddings_deployment` | Applied AI Team | On embeddings upgrade | Same approval process as primary deployment |
| `S3_CONVERSATION_LOGS_BUCKET` | all | Terraform output `conversation_logs_bucket` (AWS account) | Platform Engineering | N/A (infrastructure identifier) | Lifecycle and bucket policies managed by Terraform; Monitoring Agent verifies encryption flag nightly |
| `S3_SUMMARIES_BUCKET` | all | Terraform output `summaries_bucket` | Platform Engineering | N/A | Daily summary job checks bucket existence before upload |
| `S3_BUCKET_THERAPISTS` | all | Terraform output `therapists_bucket` | Data Ops | N/A | Data Sync Agent uploads to prefixed folders per locale |
| `SMS_PROVIDER_API_KEY` | staging / prod | AWS Secrets Manager `mindwell/sms-provider` | Growth Engineering | 60 days per vendor SLA | GitHub Actions workflow fetches secret during deployment and injects into AKS secret |
| `GOOGLE_OAUTH_CLIENT_SECRET` | staging / prod | 1Password vault `MindWell OAuth` + Azure Key Vault replica | Mobile Team | 180 days / on incident | Rotation runbook `docs/security/oauth_rotation.md` issues new secret, updates Firebase + Key Vault |
| `AZURE_SPEECH_KEY` | staging / prod | Azure Key Vault secret `azure-speech-key` | Voice Experience | 90 days | Monitoring Agent alarms if key age > 100 days |
| `BEDROCK_MODEL_ID` | dev / staging / prod | Terraform variable `bedrock_model_id` | Platform Engineering | On fallback provider change | Terraform apply triggered by infra release pipeline |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | dev (local only) | `.env.local` generated via `scripts/bootstrap-local-env.sh` | Platform Engineering | As needed when sandbox IAM user rotated | Local bootstrap script pulls credentials using `aws sts assume-role` |
| `APP_INSIGHTS_API_KEY` | staging / prod | Azure Key Vault `kv-mindwell-<env>` secret `app-insights-api-key` | SRE | 90 days | Monitoring Agent verifies key expiry and raises an alert 7 days prior |
| `ALERT_WEBHOOK_URL` | staging / prod | Azure Key Vault secret `alerting-webhook-url` | SRE | On channel rotation / quarterly review | GitHub Actions deployment injects value into AKS secret consumed by Monitoring Agent |

### Classification Cheat Sheet
- **Mandatory:** Required for service startup; missing variables cause boot failure.
- **Conditional:** Optional but recommended for production (e.g. Azure Speech keys).
- **Development-only:** Used for local tooling only; never configured in shared environments.

An authoritative CSV export for compliance reporting is generated by `scripts/dump-env-matrix.py` (see below).

## Automation & Compliance Artifacts
- `scripts/dump-env-matrix.py`: Produces an audit-friendly CSV summarizing the table above. Used by Compliance monthly.
- `infra/terraform/outputs.tf`: Publishes bucket ARNs, Key Vault URIs, and OIDC audience strings consumed during deployment.
- `docs/security/oauth_rotation.md`: Outlines the Google OAuth rotation process referenced above.
