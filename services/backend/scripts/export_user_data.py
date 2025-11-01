"""Export a user's data footprint as a JSON bundle."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.services.data_subject import DataSubjectService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a MindWell user's data (chat transcripts, summaries, memories)."
    )
    parser.add_argument("user_id", help="User UUID to export.")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Optional output file path (defaults to stdout).",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation level for readability (default 2).",
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
        export = await service.export_user_data(user_id)

    serialized = json.dumps(
        export.model_dump(by_alias=True),
        ensure_ascii=False,
        indent=args.indent if args.indent >= 0 else None,
    )

    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
        print(f"Wrote export bundle to {args.output}")
    else:
        print(serialized)

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
