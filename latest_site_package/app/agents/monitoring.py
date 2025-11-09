from __future__ import annotations

import argparse
import asyncio
import logging

from app.core.config import get_settings
from app.services.monitoring import MonitoringService


logger = logging.getLogger("mindwell.monitoring_agent")


async def _run(dry_run: bool) -> None:
    settings = get_settings()
    service = MonitoringService(settings)
    alerts = await service.run(dispatch=not dry_run)

    summary = ", ".join(f"{alert.metric}={alert.status}" for alert in alerts)
    logger.info("Monitoring checks completed: %s", summary)

    if dry_run:
        logger.info("Dry run enabled; alert dispatch skipped.")
        return


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")

    parser = argparse.ArgumentParser(
        prog="mindwell-monitoring-agent",
        description="Run MindWell observability guardrails and dispatch alerts when thresholds are exceeded.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute checks without dispatching alerts (useful for CI or validation).",
    )
    args = parser.parse_args()

    asyncio.run(_run(dry_run=args.dry_run))


if __name__ == "__main__":  # pragma: no cover - script entry point
    main()
