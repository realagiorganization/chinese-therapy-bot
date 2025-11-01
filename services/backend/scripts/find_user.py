"""Locate users by identifier to assist with SAR triage."""

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
        description="Search for MindWell users by email, phone number, or external ID."
    )
    parser.add_argument("--user-id", dest="user_id", help="User UUID to match.")
    parser.add_argument("--email", help="Email address to match exactly.")
    parser.add_argument("--phone", dest="phone_number", help="Phone number to match exactly.")
    parser.add_argument("--external-id", dest="external_id", help="External identity provider ID.")
    parser.add_argument(
        "--output",
        choices=["json", "pretty"],
        default="pretty",
        help="Output format (default pretty).",
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    if not any((args.user_id, args.email, args.phone_number, args.external_id)):
        print("At least one identifier must be provided.", file=sys.stderr)
        return 1

    user_id: UUID | None = None
    if args.user_id:
        try:
            user_id = UUID(args.user_id)
        except ValueError:
            print("Invalid user UUID supplied.", file=sys.stderr)
            return 2

    settings = get_settings()
    session_factory = get_session_factory()

    async with session_factory() as session:
        service = DataSubjectService(session, settings)
        matches = await service.find_user(
            user_id=user_id,
            email=args.email,
            phone_number=args.phone_number,
            external_id=args.external_id,
        )

    if args.output == "json":
        print(
            json.dumps(
                [match.model_dump(by_alias=True) for match in matches],
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        if not matches:
            print("No users found.")
        for match in matches:
            payload = match.model_dump(by_alias=True)
            print(f"- id: {payload['id']}")
            print(f"  email: {payload.get('email')}")
            print(f"  phone: {payload.get('phoneNumber')}")
            print(f"  locale: {payload.get('locale')}")
            print(f"  createdAt: {payload.get('createdAt')}")
            print("")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
