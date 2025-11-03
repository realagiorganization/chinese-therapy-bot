"""Summarize pilot feedback to support UAT prioritization."""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Iterable

from app.core.database import get_session_factory
from app.schemas.feedback import PilotFeedbackFilters
from app.services.feedback import PilotFeedbackService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize pilot feedback sentiment, trust, usability, and themes."
    )
    parser.add_argument("--cohort", help="Optional cohort filter (e.g. pilot-2025w4).")
    parser.add_argument("--channel", help="Optional channel filter (e.g. web, mobile).")
    parser.add_argument("--role", help="Optional participant role filter.")
    parser.add_argument(
        "--minimum-trust-score",
        type=int,
        default=None,
        help="Filter results to trust scores >= N (1-5).",
    )
    parser.add_argument(
        "--format",
        choices=("human", "json"),
        default="human",
        help="Output format (default: human-readable).",
    )
    parser.add_argument(
        "--top-tag-limit",
        type=int,
        default=8,
        help="Maximum number of tags to include in the summary (default: 8).",
    )
    return parser.parse_args()


def _format_average(label: str, value: float | None) -> str:
    if value is None:
        return f"{label}: -"
    return f"{label}: {value:.2f}"


def _print_grouped(
    header: str,
    groups: Iterable,
) -> None:
    groups = list(groups)
    if not groups:
        return

    print(f"\n{header}:")
    print("  key                total  sentiment  trust  usability  follow-ups")
    print("  -----------------------------------------------------------------")
    for group in groups:
        sentiment = f"{group.average_sentiment:.2f}" if group.average_sentiment is not None else "-"
        trust = f"{group.average_trust:.2f}" if group.average_trust is not None else "-"
        usability = f"{group.average_usability:.2f}" if group.average_usability is not None else "-"
        print(
            f"  {group.key:<18} {group.total:>5}  {sentiment:>9}  {trust:>5}  {usability:>9}  {group.follow_up_needed:>10}"
        )


async def main() -> int:
    args = parse_args()
    filters = PilotFeedbackFilters(
        cohort=args.cohort or None,
        channel=args.channel or None,
        role=args.role or None,
        minimum_trust_score=args.minimum_trust_score,
    )

    session_factory = get_session_factory()
    async with session_factory() as session:
        service = PilotFeedbackService(session)
        summary = await service.summarize_feedback(filters, top_tag_limit=args.top_tag_limit)

    if args.format == "json":
        print(summary.model_dump_json(indent=2, ensure_ascii=False))
        return 0

    print("Pilot Feedback Summary")
    print("======================")
    print(f"Total entries: {summary.total_entries}")
    print(_format_average("Average sentiment", summary.average_sentiment))
    print(_format_average("Average trust", summary.average_trust))
    print(_format_average("Average usability", summary.average_usability))
    print(f"Follow-ups needed: {summary.follow_up_needed}")

    if summary.top_tags:
        print("\nTop tags:")
        for entry in summary.top_tags:
            print(f"  - {entry.tag} ({entry.count})")

    _print_grouped("By cohort", summary.by_cohort)
    _print_grouped("By channel", summary.by_channel)
    _print_grouped("By role", summary.by_role)

    return 0


def cli() -> int:
    """Entry point compatible with console_scripts."""
    return asyncio.run(main())


if __name__ == "__main__":
    raise SystemExit(cli())
