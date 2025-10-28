# MindWell Backend Service

This package scaffolds the core MindWell API platform using FastAPI. It aligns with Phase 3 of the development plan by defining clear module boundaries for authentication, chat orchestration, therapist data, and reporting pipelines.

## Project Layout

```
services/backend/
  app/
    api/         # FastAPI routers grouped by vertical (auth, chat, therapists, reports)
    core/        # Settings, logging, application factory
    models/      # ORM models (placeholder)
    schemas/     # Pydantic schemas shared by endpoints
    services/    # Business logic and integrations (LLM orchestration, storage, etc.)
    main.py      # Entrypoint wiring routers and startup hooks
```

## Quick Start

```bash
cd services/backend
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
mindwell-api
```

By default the API listens on `http://0.0.0.0:8000`. The current implementation exposes stub endpoints (health, auth, chat, therapists, reports) that illustrate the modular architecture without connecting to external systems yet.

## Environment Configuration

Application settings are defined in `app/core/config.py` using `pydantic-settings`. Populate a `.env` file or environment variables for the following fields as they become available:

- `APP_ENV`
- `OPENAI_API_KEY`
- `DATABASE_URL`
- `AWS_REGION`
- `S3_SUMMARIES_BUCKET`

## Next Steps

- Flesh out persistence models in `app/models` backed by SQLAlchemy.
- Connect authentication routes to SMS OTP and Google OAuth providers.
- Implement streaming chat orchestration that bridges Azure OpenAI and AWS Bedrock.
- Wire background tasks for summary generation and therapist data sync.
