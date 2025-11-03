"""Generate follow-up recommendations for pilot cohort engagement."""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from app.core.database import get_session_factory
from app.schemas.pilot_cohort import (
    PilotParticipantFilters,
    PilotParticipantStatus,
)
from app.services.pilot_cohort import PilotCohortService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan pilot cohort follow-ups and render actionable messaging."
    )
    parser.add_argument("--cohort", help="Optional cohort identifier filter (e.g. pilot-2025w6).")
    parser.add_argument(
        "--status",
        choices=[status.value for status in PilotParticipantStatus],
        help="Optional participant status filter applied before computing follow-ups.",
    )
    parser.add_argument("--channel", help="Optional preferred channel filter (e.g. web or wechat).")
    parser.add_argument(
        "--horizon-days",
        type=int,
        default=7,
        help="Include follow-ups occurring within the next N days (default: 7, max: 30).",
    )
    parser.add_argument(
        "--format",
        choices=("human", "json"),
        default="human",
        help="Output format for follow-up recommendations.",
    )
    return parser.parse_args()


async def _collect_followups(args: argparse.Namespace) -> Any:
    horizon = max(1, min(args.horizon_days, 30))
    filters = PilotParticipantFilters(
        cohort=args.cohort or None,
        status=PilotParticipantStatus(args.status) if args.status else None,
        channel=args.channel or None,
    )

    session_factory = get_session_factory()
    async with session_factory() as session:
        service = PilotCohortService(session)
        plan = await service.plan_followups(filters, horizon_days=horizon)
    return plan


def _print_human(plan) -> None:
    print("Pilot Follow-up Plan")
    print("====================")
    print(f"Generated at: {plan.generated_at.isoformat()}")
    print(f"Total follow-ups: {plan.total}")
    if not plan.items:
        print("\nNo follow-ups fall within the selected horizon.")
        return

    for item in plan.items:
        display_name = item.participant_alias or str(item.participant_id)
        due_date = item.due_at.strftime("%Y-%m-%d")
        print(
            f"\n- {display_name} | Cohort {item.cohort} | Status {item.status.value} | "
            f"Channel {item.channel}"
        )
        print(f"  Due: {due_date} ({item.urgency.value})")
        print(f"  Reason: {item.reason}")
        print(f"  Subject: {item.subject}")
        print(f"  Message: {item.message}")


def main() -> int:
    args = parse_args()
    plan = asyncio.run(_collect_followups(args))
    if args.format == "json":
        print(plan.model_dump_json(indent=2, ensure_ascii=False))
        return 0

    _print_human(plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
