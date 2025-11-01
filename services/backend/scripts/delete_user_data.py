"""Redact and remove user-specific data for a SAR deletion request."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from uuid import UUID

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.services.data_subject import DataSubjectService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Redact chat transcripts, summaries, and revoke tokens for a MindWell user."
    )
    parser.add_argument("user_id", help="User UUID to delete/redact.")
    parser.add_argument(
        "--redaction-token",
        default="[redacted]",
        help="Text used to replace chat message content (default: [redacted]).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute without committing changes (database rollback).",
    )
    parser.add_argument(
        "--output",
        choices=["json", "pretty"],
        default="pretty",
        help="Output format for the deletion report.",
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    try:
        user_id = UUID(args.user_id)
    except ValueError:
        print("Invalid user UUID supplied.", file=sys.stderr)
        return 2

    settings = get_settings()
    session_factory = get_session_factory()

    async with session_factory() as session:
        service = DataSubjectService(session, settings)
        try:
            report = await service.delete_user_data(
                user_id,
                redaction_token=args.redaction_token,
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            await session.rollback()
            return 3

        if args.dry_run:
            await session.rollback()
        else:
            await session.commit()

    payload = report.model_dump(by_alias=True)
    if args.output == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if args.dry_run:
            print("[dry-run] changes were rolled back.")
        for key, value in payload.items():
            print(f"{key}: {value}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
