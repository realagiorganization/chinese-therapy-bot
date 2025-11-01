from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import date

from app.core.config import get_settings
from app.services.summaries import SummaryScheduler


logger = logging.getLogger("mindwell.summary_scheduler")


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid date '{value}'. Expected YYYY-MM-DD.") from exc


async def _run(mode: str, target: date | None) -> None:
    settings = get_settings()
    scheduler = SummaryScheduler(settings)
    target_date = target or date.today()

    if mode in {"daily", "both"}:
        generated = await scheduler.run_daily(target_date=target_date)
        logger.info("Generated %s daily summaries for %s.", generated, target_date.isoformat())
    if mode in {"weekly", "both"}:
        generated = await scheduler.run_weekly(anchor_date=target_date)
        logger.info("Generated %s weekly summaries anchored at %s.", generated, target_date.isoformat())


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")

    parser = argparse.ArgumentParser(
        prog="mindwell-summary-scheduler",
        description="Generate daily or weekly MindWell conversation summaries.",
    )
    parser.add_argument(
        "mode",
        nargs="?",
        choices=("daily", "weekly", "both"),
        default="daily",
        help="Summary cadence to run (default: daily).",
    )
    parser.add_argument(
        "--date",
        dest="date_value",
        default=None,
        type=_parse_date,
        help="Anchor date in YYYY-MM-DD (defaults to today).",
    )
    args = parser.parse_args()

    target = args.date_value if isinstance(args.date_value, date) else None
    asyncio.run(_run(args.mode, target))


if __name__ == "__main__":
    main()
