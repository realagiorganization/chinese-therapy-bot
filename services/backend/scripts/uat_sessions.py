"""CLI utilities for logging pilot UAT sessions."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from uuid import UUID

from app.core.database import get_session_factory
from app.schemas.pilot_uat import PilotUATIssue, PilotUATSessionCreate
from app.services.pilot_uat import PilotUATService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mindwell-uat-sessions",
        description="Log and inspect pilot UAT session results.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    record_parser = subparsers.add_parser(
        "record",
        help="Record a single UAT session entry from CLI flags.",
    )
    _add_common_session_arguments(record_parser)
    record_parser.add_argument(
        "--issue",
        action="append",
        default=[],
        help="Add an issue using 'severity:title:notes' format (notes optional).",
    )
    record_parser.add_argument(
        "--action-item",
        action="append",
        default=[],
        dest="action_items",
        help="Add a follow-up action item.",
    )
    record_parser.add_argument(
        "--metadata",
        type=str,
        help="JSON string containing additional metadata to persist.",
    )

    import_parser = subparsers.add_parser(
        "import",
        help="Import multiple sessions from a CSV file.",
    )
    import_parser.add_argument(
        "path",
        type=Path,
        help="Path to the CSV file containing session rows.",
    )
    import_parser.add_argument(
        "--cohort",
        type=str,
        help="Override cohort for all imported rows (falls back to CSV column).",
    )

    return parser


def _add_common_session_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--cohort", required=True, help="Pilot cohort identifier (e.g. pilot-2025w4).")
    parser.add_argument("--participant-alias", help="Participant alias or anonymized identifier.")
    parser.add_argument("--participant-id", help="UUID of the participant in roster table.")
    parser.add_argument(
        "--session-date",
        help="ISO8601 timestamp for when the session occurred (defaults to current UTC).",
    )
    parser.add_argument("--facilitator", help="Who facilitated the session (role or name).")
    parser.add_argument("--scenario", help="Scenario exercised during the session.")
    parser.add_argument("--environment", help="Environment identifier (qa, pilot, prod).")
    parser.add_argument("--platform", help="Platform used (web, mobile, ios, android).")
    parser.add_argument("--device", help="Device metadata (e.g. iPhone 12, Redmi 11).")
    parser.add_argument(
        "--satisfaction-score",
        type=int,
        default=3,
        help="Participant satisfaction score from 1-5.",
    )
    parser.add_argument(
        "--trust-score",
        type=int,
        help="Optional trust score from 1-5.",
    )
    parser.add_argument("--highlights", help="Key highlights captured during the session.")
    parser.add_argument("--blockers", help="Blocking issues observed.")
    parser.add_argument("--notes", help="Additional facilitator notes.")


async def _log_record(args: argparse.Namespace) -> None:
    session_factory = get_session_factory()
    async with session_factory() as db_session:
        service = PilotUATService(db_session)
        metadata = json.loads(args.metadata) if args.metadata else None
        issues = [_parse_issue(value) for value in args.issue]
        payload = PilotUATSessionCreate(
            cohort=args.cohort,
            participant_alias=args.participant_alias,
            participant_id=_parse_uuid(args.participant_id) if args.participant_id else None,
            session_date=_parse_datetime(args.session_date),
            facilitator=args.facilitator,
            scenario=args.scenario,
            environment=args.environment,
            platform=args.platform,
            device=args.device,
            satisfaction_score=args.satisfaction_score,
            trust_score=args.trust_score,
            highlights=args.highlights,
            blockers=args.blockers,
            notes=args.notes,
            issues=issues,
            action_items=args.action_items,
            metadata=metadata,
        )
        record = await service.log_session(payload)
        await db_session.commit()
        alias = record.participant_alias or "(unspecified)"
        print(f"Logged UAT session {record.id} for participant {alias} in cohort {record.cohort}.")


async def _import_records(args: argparse.Namespace) -> None:
    if not args.path.exists():
        raise FileNotFoundError(f"CSV file not found: {args.path}")

    rows = list(_read_csv(args.path))
    if not rows:
        print("No rows found in CSV; nothing to import.")
        return

    session_factory = get_session_factory()
    async with session_factory() as db_session:
        service = PilotUATService(db_session)
        created = 0
        for row in rows:
            cohort_value = (args.cohort or row.get("cohort") or "").strip()
            if not cohort_value:
                raise ValueError("Cohort column required for each row unless --cohort is provided.")

            payload = PilotUATSessionCreate(
                cohort=cohort_value,
                participant_alias=row.get("participant_alias") or row.get("alias"),
                participant_id=_parse_uuid(row.get("participant_id")) if row.get("participant_id") else None,
                session_date=_parse_datetime(row.get("session_date")),
                facilitator=row.get("facilitator"),
                scenario=row.get("scenario"),
                environment=row.get("environment"),
                platform=row.get("platform"),
                device=row.get("device"),
                satisfaction_score=_parse_int(row.get("satisfaction_score"), default=3),
                trust_score=_parse_optional_int(row.get("trust_score")),
                highlights=row.get("highlights"),
                blockers=row.get("blockers"),
                notes=row.get("notes"),
                issues=[_parse_issue(issue) for issue in _split_iter(row.get("issues"))],
                action_items=list(_split_iter(row.get("action_items"))),
                metadata=_parse_metadata(row.get("metadata")),
            )
            await service.log_session(payload)
            created += 1

        await db_session.commit()
        print(f"Imported {created} UAT session(s) from {args.path}.")


def _parse_issue(raw: str) -> PilotUATIssue:
    severity = title = notes = None
    if raw:
        parts = [part.strip() for part in raw.split(":", 2)]
        if len(parts) == 1:
            title = parts[0]
        elif len(parts) == 2:
            severity, title = parts
        else:
            severity, title, notes = parts
    if not title:
        raise ValueError("Issue entries must include a title (optionally severity:notes).")
    return PilotUATIssue(title=title, severity=severity or None, notes=notes or None)


def _parse_uuid(value: str) -> UUID:
    return UUID(value.strip())


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    timestamp = datetime.fromisoformat(value.strip())
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _parse_int(value: str | None, *, default: int) -> int:
    if value is None or value == "":
        return default
    return int(value)


def _parse_optional_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _split_iter(value: str | None) -> Iterable[str]:
    if not value:
        return []
    return [item for item in (part.strip() for part in value.split("|")) if item]


def _parse_metadata(value: str | None) -> dict | None:
    if not value:
        return None
    return json.loads(value)


def _read_csv(path: Path) -> Iterable[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield row


def cli(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "record":
        asyncio.run(_log_record(args))
    elif args.command == "import":
        asyncio.run(_import_records(args))
    else:  # pragma: no cover - argparse enforces choices
        parser.print_help()


if __name__ == "__main__":  # pragma: no cover
    cli()
