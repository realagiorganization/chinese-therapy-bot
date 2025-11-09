# MindWell Load Testing

This directory contains Locust scenarios that simulate end-to-end usage of the MindWell API. Each virtual user alternates between:

- posting chat turns to `/api/chat/message` in non-streaming mode,
- querying the therapist directory via `/api/therapists/`,
- and fetching the journey report from `/api/reports/journey` (when a session exists).

## Prerequisites

- Python 3.10+
- [Locust](https://locust.io/) installed: `pip install locust`
- Running backend API (e.g., `make run` from `services/backend/`)

## Running

1. Start the API locally (from `services/backend`): `mindwell-api`
2. In a separate shell:

   ```bash
   cd services/backend
   locust -f loadtests/locustfile.py --host http://localhost:8000
   ```

Environment variables:

- `MW_BACKEND_HOST`: overrides the host passed to Locust (useful for remote environments).

You can drive load through the web UI (http://localhost:8089) or CLI, e.g.:

```bash
locust -f loadtests/locustfile.py --headless -u 50 -r 10 -t 10m
```

The scenario records failures when responses are non-200, malformed, or missing required keys so regressions surface quickly.
