"""Utility CLI for managing pilot cohort participants."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Iterable
from uuid import UUID

from app.core.database import get_session_factory
from app.schemas.pilot_cohort import (
    PilotParticipantCreate,
    PilotParticipantFilters,
    PilotParticipantStatus,
    PilotParticipantSummary,
    PilotParticipantSummaryBucket,
    PilotParticipantUpdate,
)
from app.services.pilot_cohort import PilotCohortService


def _status_choices() -> list[str]:
    return [status.value for status in PilotParticipantStatus]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mindwell-pilot-cohort",
        description="Manage pilot cohort participant roster.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser(
        "import",
        help="Import participants from a CSV file.",
    )
    import_parser.add_argument(
        "path",
        type=Path,
        help="CSV file with columns: alias,email,phone,status,channel,locale,source,tags,consent,notes,metadata,invite_sent_at,onboarded_at,last_contacted_at",
    )
    import_parser.add_argument(
        "--cohort",
        required=True,
        help="Cohort identifier applied when missing from CSV.",
    )
    import_parser.add_argument(
        "--channel",
        default="web",
        help="Default channel if the CSV omits it.",
    )
    import_parser.add_argument(
        "--locale",
        default="zh-CN",
        help="Default locale if the CSV omits it.",
    )
    import_parser.add_argument(
        "--status",
        default="invited",
        choices=_status_choices(),
        help="Default status if the CSV omits it.",
    )
    import_parser.add_argument(
        "--source",
        default=None,
        help="Default acquisition source when omitted.",
    )
    import_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse CSV rows without writing to the database.",
    )
    import_parser.set_defaults(command="import")

    list_parser = subparsers.add_parser(
        "list",
        help="List participants with optional filters.",
    )
    list_parser.add_argument("--cohort", help="Filter by cohort identifier.")
    list_parser.add_argument("--status", choices=_status_choices(), help="Filter by status.")
    list_parser.add_argument("--channel", help="Filter by preferred channel.")
    list_parser.add_argument("--source", help="Filter by acquisition source.")
    list_parser.add_argument("--search", help="Case-insensitive search term.")
    consent_group = list_parser.add_mutually_exclusive_group()
    consent_group.add_argument(
        "--consent-required",
        action="store_const",
        const=False,
        dest="consent",
        help="Only participants without consent acknowledgement.",
    )
    consent_group.add_argument(
        "--consent-complete",
        action="store_const",
        const=True,
        dest="consent",
        help="Only participants with consent acknowledgement.",
    )
    list_parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum records to display (default: 50).",
    )
    list_parser.set_defaults(command="list", consent=None)

    summary_parser = subparsers.add_parser(
        "summary",
        help="Show aggregate pilot cohort metrics.",
    )
    summary_parser.add_argument("--cohort", help="Filter by cohort identifier.")
    summary_parser.add_argument("--status", choices=_status_choices(), help="Filter by status.")
    summary_parser.add_argument("--channel", help="Filter by preferred channel.")
    summary_parser.add_argument("--source", help="Filter by acquisition source.")
    consent_group = summary_parser.add_mutually_exclusive_group()
    consent_group.add_argument(
        "--consent-required",
        action="store_const",
        const=False,
        dest="consent",
        help="Only participants without consent acknowledgement.",
    )
    consent_group.add_argument(
        "--consent-complete",
        action="store_const",
        const=True,
        dest="consent",
        help="Only participants with consent acknowledgement.",
    )
    summary_parser.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="Output format for the summary (default: table).",
    )
    summary_parser.set_defaults(command="summary", consent=None)

    update_parser = subparsers.add_parser(
        "update",
        help="Update a single participant by UUID.",
    )
    update_parser.add_argument(
        "participant_id",
        help="Participant UUID to update.",
    )
    update_parser.add_argument("--status", choices=_status_choices(), help="Set a new status.")
    update_parser.add_argument(
        "--consent",
        choices=("true", "false"),
        help="Mark consent received (true) or pending (false).",
    )
    update_parser.add_argument(
        "--tags",
        help="Pipe-separated tags that replace existing tags (use empty string to clear).",
    )
    update_parser.add_argument("--notes", help="Replace internal notes content.")
    update_parser.add_argument("--source", help="Update acquisition source.")
    update_parser.add_argument("--channel", help="Update preferred channel.")
    update_parser.add_argument("--locale", help="Update locale preference.")
    update_parser.set_defaults(command="update")

    return parser


def _parse_tags(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    if raw.strip() == "":
        return []
    separators = ["|", ",", ";"]
    for separator in separators:
        if separator in raw:
            tokens = [item.strip() for item in raw.split(separator)]
            break
    else:
        tokens = [raw.strip()]
    return [token for token in tokens if token]


def _parse_bool(raw: str | None) -> bool | None:
    if raw is None:
        return None
    normalized = raw.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"Unable to parse boolean value from '{raw}'.")


def _parse_datetime(raw: str | None):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:  # pragma: no cover - invalid input
        raise ValueError(f"Invalid datetime value '{raw}'. Expected ISO8601 format.") from exc


async def handle_import(args: argparse.Namespace) -> int:
    session_factory = get_session_factory()
    created = 0
    async with session_factory() as session:
        service = PilotCohortService(session)
        rows = _read_csv(args.path)
        for row in rows:
            cohort = row.get("cohort") or args.cohort
            status_value = row.get("status") or args.status
            try:
                status = PilotParticipantStatus(status_value.strip())
            except Exception as exc:
                raise ValueError(f"Unsupported status '{status_value}' in row {row}") from exc

            metadata = _parse_metadata(row.get("metadata"))
            tags = _parse_tags(row.get("tags")) or []
            if row.get("consent") is not None:
                consent = _parse_bool(row.get("consent"))
            else:
                consent = None

            payload = PilotParticipantCreate(
                cohort=cohort,
                participant_alias=row.get("alias"),
                contact_email=row.get("email"),
                contact_phone=row.get("phone"),
                channel=row.get("channel") or args.channel,
                locale=row.get("locale") or args.locale,
                status=status,
                source=row.get("source") or args.source,
                tags=tags,
                invite_sent_at=_parse_datetime(row.get("invite_sent_at")),
                onboarded_at=_parse_datetime(row.get("onboarded_at")),
                last_contacted_at=_parse_datetime(row.get("last_contacted_at")),
                consent_received=consent if consent is not None else False,
                notes=row.get("notes"),
                metadata=metadata,
            )
            if args.dry_run:
                created += 1
                continue

            await service.create_participant(payload)
            created += 1

        if args.dry_run:
            await session.rollback()
        else:
            await session.commit()

    action = "Validated" if args.dry_run else "Imported"
    print(f"{action} {created} participant(s).")
    return 0


def _parse_metadata(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:  # pragma: no cover - invalid input
        raise ValueError(f"Invalid metadata JSON: {raw}") from exc


def _read_csv(path: Path) -> Iterable[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield {key.strip(): (value or "").strip() for key, value in row.items()}


async def handle_list(args: argparse.Namespace) -> int:
    session_factory = get_session_factory()
    async with session_factory() as session:
        service = PilotCohortService(session)
        filters = PilotParticipantFilters(
            cohort=args.cohort,
            status=PilotParticipantStatus(args.status) if args.status else None,
            channel=args.channel,
            source=args.source,
            consent_received=args.consent,
            search=args.search,
        )
        response = await service.list_participants(filters, limit=args.limit)

    if not response.items:
        print("No participants found.")
        return 0

    print("ID                                    Cohort          Status       Consent  Email / Alias")
    print("------------------------------------------------------------------------------------------")
    for item in response.items:
        consent = "yes" if item.consent_received else "no"
        identifier = item.contact_email or item.participant_alias or "-"
        print(
            f"{item.id}  {item.cohort:<14} {item.status.value:<11} {consent:<7} {identifier}"
        )
    print(f"\nTotal: {response.total}")
    return 0


async def handle_update(args: argparse.Namespace) -> int:
    session_factory = get_session_factory()
    participant_id = UUID(args.participant_id)
    tags = _parse_tags(args.tags) if args.tags is not None else None
    consent = _parse_bool(args.consent) if args.consent is not None else None
    async with session_factory() as session:
        service = PilotCohortService(session)
        payload = PilotParticipantUpdate(
            status=PilotParticipantStatus(args.status) if args.status else None,
            consent_received=consent,
            tags=tags,
            notes=args.notes,
            source=args.source,
            channel=args.channel,
            locale=args.locale,
        )
        participant = await service.update_participant(participant_id, payload)
        await session.commit()

    print(f"Updated {participant.id} -> status={participant.status}")
    return 0


def _percent(value: int, total: int) -> str:
    if total <= 0:
        return "0.0%"
    return f"{(value / total) * 100:.1f}%"


def _render_bucket_section(title: str, buckets: list[PilotParticipantSummaryBucket]) -> list[str]:
    if not buckets:
        return [f"{title}: no data recorded."]
    header = f"{title} (count)"
    lines = [header, "-" * len(header)]
    for bucket in buckets:
        lines.append(f"{bucket.key:<18} {bucket.total}")
    return lines


def render_summary_table(summary: PilotParticipantSummary) -> str:
    """Return a human-readable table for pilot cohort summary metrics."""
    lines = [
        f"Total participants: {summary.total}",
        f"Consent complete:   {summary.with_consent} ({_percent(summary.with_consent, summary.total)})",
        f"Consent pending:    {summary.without_consent} ({_percent(summary.without_consent, summary.total)})",
        "",
        *_render_bucket_section("Status distribution", summary.by_status),
        "",
        *_render_bucket_section("Channel distribution", summary.by_channel),
        "",
        *_render_bucket_section("Locale distribution", summary.by_locale),
    ]
    if summary.top_tags:
        lines.extend(
            [
                "",
                *_render_bucket_section("Top tags", summary.top_tags),
            ]
        )
    return "\n".join(lines)


async def handle_summary(args: argparse.Namespace) -> int:
    session_factory = get_session_factory()
    async with session_factory() as session:
        service = PilotCohortService(session)
        filters = PilotParticipantFilters(
            cohort=args.cohort,
            status=PilotParticipantStatus(args.status) if args.status else None,
            channel=args.channel,
            source=args.source,
            consent_received=args.consent,
        )
        summary = await service.summarize_participants(filters)

    if args.format == "json":
        print(json.dumps(summary.model_dump(), indent=2, ensure_ascii=False))
    else:
        print(render_summary_table(summary))
    return 0


async def dispatch(args: argparse.Namespace) -> int:
    if args.command == "import":
        return await handle_import(args)
    if args.command == "list":
        return await handle_list(args)
    if args.command == "summary":
        return await handle_summary(args)
    if args.command == "update":
        return await handle_update(args)
    raise ValueError(f"Unsupported command {args.command}")


def cli() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return asyncio.run(dispatch(args))
    except KeyboardInterrupt:  # pragma: no cover - interactive use
        return 130


if __name__ == "__main__":
    raise SystemExit(cli())
