"""Load structured pilot feedback fixtures into the database."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from sqlalchemy import delete

from app.core.database import get_session_factory
from app.models import PilotFeedback
from app.schemas.feedback import PilotFeedbackCreate
from app.services.feedback import PilotFeedbackService


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed pilot cohort feedback entries using PilotFeedbackService."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("docs/uat/pilot_cohort_feedback.json"),
        help="Path to the JSON file that contains an array of feedback entries.",
    )
    parser.add_argument(
        "--cohort",
        help="Optional cohort filter; only records matching this cohort are inserted.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete existing feedback rows for the targeted cohort(s) before inserting.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate payloads without committing database changes.",
    )
    return parser.parse_args()


def _load_entries(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Feedback fixture not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Feedback fixture must be a JSON array.")
    return data


async def _apply_seed(
    entries: list[dict[str, Any]],
    *,
    cohort_filter: str | None,
    replace: bool,
    dry_run: bool,
) -> tuple[int, int]:
    session_factory = get_session_factory()
    inserted = 0
    deleted = 0

    async with session_factory() as session:
        service = PilotFeedbackService(session)
        cohorts = {entry.get("cohort") for entry in entries if entry.get("cohort")}

        if replace:
            target_cohorts = [cohort_filter] if cohort_filter else cohorts
            for cohort in target_cohorts:
                if not cohort:
                    continue
                result = await session.execute(
                    delete(PilotFeedback).where(PilotFeedback.cohort == cohort)
                )
                deleted += result.rowcount or 0

        for entry in entries:
            cohort = entry.get("cohort")
            if cohort_filter and cohort != cohort_filter:
                continue
            payload = PilotFeedbackCreate(**entry)
            await service.record_feedback(payload)
            inserted += 1

        if dry_run:
            await session.rollback()
        else:
            await session.commit()

    return inserted, deleted


async def _main() -> int:
    args = _parse_args()
    entries = _load_entries(args.input)
    inserted, deleted = await _apply_seed(
        entries,
        cohort_filter=args.cohort,
        replace=args.replace,
        dry_run=args.dry_run,
    )
    action = "validated" if args.dry_run else "inserted"
    print(
        f"{action} {inserted} pilot feedback entr{'y' if inserted == 1 else 'ies'}"
        f"{' with ' if args.dry_run else ' and '}deleted {deleted} existing rows"
        f"{' (dry run)' if args.dry_run else ''}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
