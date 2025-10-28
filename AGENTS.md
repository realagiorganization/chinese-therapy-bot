# Automation & Agent Notes

- **CI Runner Agent:** Handles GitHub Actions workloads on EC2, responsible for building, testing, and deploying backend, frontend, and mobile artifacts.
- **Data Sync Agent:** Periodically pulls therapist data sources, normalizes entries, and uploads to `S3_BUCKET_THERAPISTS` for ingestion.
- **Summary Scheduler Agent:** Triggers daily and weekly conversation summary jobs, ensuring outputs persist to the summaries bucket.
- **Monitoring Agent:** Watches observability dashboards and raises alerts when latency, error rates, or cost thresholds exceed defined budgets.
