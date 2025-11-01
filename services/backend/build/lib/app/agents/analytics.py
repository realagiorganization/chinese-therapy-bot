from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path

from app.core.database import session_scope
from app.services.analytics import ProductAnalyticsService


logger = logging.getLogger("mindwell.analytics_agent")


async def _run(window_hours: int, output: Path | None) -> None:
    async with session_scope() as session:
        service = ProductAnalyticsService(session)
        summary = await service.summarize(window_hours=window_hours)
        payload = summary.model_dump(mode="json")

    formatted = json.dumps(payload, ensure_ascii=False, indent=2)
    if output:
        output.write_text(formatted, encoding="utf-8")
        logger.info("Wrote analytics summary to %s", output)
    else:
        print(formatted)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")

    parser = argparse.ArgumentParser(
        prog="mindwell-analytics-agent",
        description="Generate product analytics summary snapshots for growth planning.",
    )
    parser.add_argument(
        "--window-hours",
        type=int,
        default=24,
        help="Time window (in hours) to aggregate (default: 24).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write the analytics summary as JSON.",
    )
    args = parser.parse_args()

    asyncio.run(_run(args.window_hours, args.output))


if __name__ == "__main__":
    main()
