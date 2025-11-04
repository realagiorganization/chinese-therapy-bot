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
from app.schemas.pilot_uat import (
    PilotUATGroupSummary,
    PilotUATIssue,
    PilotUATIssueSummary,
    PilotUATSessionCreate,
    PilotUATSessionFilters,
    PilotUATSessionResponse,
    PilotUATSessionSummary,
)
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

    report_parser = subparsers.add_parser(
        "report",
        help="Generate a markdown digest summarizing recorded UAT sessions.",
    )
    report_parser.add_argument("--cohort", help="Filter report data by cohort code.")
    report_parser.add_argument(
        "--environment",
        help="Filter by environment (qa, pilot, prod, etc.).",
    )
    report_parser.add_argument(
        "--since",
        dest="occurred_after",
        help="Only include sessions that occurred on/after this ISO8601 timestamp.",
    )
    report_parser.add_argument(
        "--until",
        dest="occurred_before",
        help="Only include sessions that occurred on/before this ISO8601 timestamp.",
    )
    report_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Number of recent sessions to append to the digest (default: 5).",
    )
    report_parser.add_argument(
        "--output",
        type=Path,
        help="If provided, write the markdown digest to this file path.",
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


async def _generate_report(args: argparse.Namespace) -> None:
    session_factory = get_session_factory()
    async with session_factory() as db_session:
        service = PilotUATService(db_session)
        filters = PilotUATSessionFilters(
            cohort=args.cohort,
            environment=args.environment,
            occurred_after=_parse_datetime(args.occurred_after),
            occurred_before=_parse_datetime(args.occurred_before),
        )
        summary = await service.summarize_sessions(filters)
        list_response = await service.list_sessions(filters, limit=args.limit, offset=0)
        markdown = render_markdown_digest(summary, list_response.items)

    output_path: Path | None = args.output
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
    print(markdown)


def render_markdown_digest(
    summary: PilotUATSessionSummary,
    recent_sessions: Iterable[PilotUATSessionResponse],
) -> str:
    """Render a human-readable markdown digest for pilot UAT activity."""
    lines: list[str] = ["# Pilot UAT Digest", ""]
    lines.extend(_render_summary_metrics(summary))
    lines.append("")
    lines.extend(_render_issue_table(summary.issues_by_severity))
    lines.append("")
    lines.extend(_render_group_table("Sessions by Platform", summary.sessions_by_platform))
    lines.append("")
    lines.extend(_render_group_table("Sessions by Environment", summary.sessions_by_environment))
    lines.append("")
    lines.extend(_render_recent_sessions(recent_sessions))
    return "\n".join(lines).strip() + "\n"


def _render_summary_metrics(summary: PilotUATSessionSummary) -> list[str]:
    if summary.total_sessions == 0:
        return ["No pilot UAT sessions have been recorded yet."]

    def _format_optional(value: float | None) -> str:
        return f"{value:.2f}" if value is not None else "n/a"

    return [
        f"- Total sessions: **{summary.total_sessions}**",
        f"- Distinct participants: **{summary.distinct_participants}**",
        f"- Average satisfaction: **{_format_optional(summary.average_satisfaction)} / 5**",
        f"- Average trust: **{_format_optional(summary.average_trust)} / 5**",
        f"- Sessions reporting blockers: **{summary.sessions_with_blockers}**",
    ]


def _render_issue_table(issues: Iterable[PilotUATIssueSummary]) -> list[str]:
    issues = list(issues)
    if not issues:
        return ["## Issue Counts by Severity", "", "_No issues logged yet._"]

    lines = ["## Issue Counts by Severity", "", "| Severity | Count |", "| --- | --- |"]
    for issue in issues:
        label = issue.severity or "unspecified"
        lines.append(f"| {label} | {issue.count} |")
    return lines


def _render_group_table(
    title: str,
    groups: Iterable[PilotUATGroupSummary],
) -> list[str]:
    groups = list(groups)
    if not groups:
        return [f"## {title}", "", "_No data available._"]

    def _format_optional(value: float | None) -> str:
        return f"{value:.2f}" if value is not None else "n/a"

    lines = [
        f"## {title}",
        "",
        "| Key | Sessions | Avg. Satisfaction | Avg. Trust |",
        "| --- | --- | --- | --- |",
    ]
    for group in groups:
        lines.append(
            f"| {group.key} | {group.total} | {_format_optional(group.average_satisfaction)} | "
            f"{_format_optional(group.average_trust)} |"
        )
    return lines


def _render_recent_sessions(
    sessions: Iterable[PilotUATSessionResponse],
) -> list[str]:
    sessions = list(sessions)
    if not sessions:
        return ["## Recent Sessions", "", "_No sessions to display._"]

    lines = ["## Recent Sessions", ""]
    for session in sessions:
        timestamp = session.session_date.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        alias = session.participant_alias or "anonymous"
        platform = session.platform or "unspecified"
        highlights = session.highlights or "—"
        blockers = session.blockers or "—"
        lines.extend(
            [
                f"### {timestamp} · {alias} · {platform}",
                f"- Satisfaction: **{session.satisfaction_score} / 5**, Trust: "
                f"**{session.trust_score if session.trust_score is not None else 'n/a'} / 5**",
                f"- Facilitator: {session.facilitator or 'unspecified'} · Scenario: "
                f"{session.scenario or 'unspecified'}",
                f"- Highlights: {highlights}",
                f"- Blockers: {blockers}",
            ]
        )
        if session.issues:
            issue_lines = ", ".join(f"{issue.severity or 'unspecified'} – {issue.title}" for issue in session.issues)
            lines.append(f"- Issues: {issue_lines}")
        if session.action_items:
            lines.append(f"- Action Items: {', '.join(session.action_items)}")
        lines.append("")
    return lines


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
    elif args.command == "report":
        asyncio.run(_generate_report(args))
    else:  # pragma: no cover - argparse enforces choices
        parser.print_help()


if __name__ == "__main__":  # pragma: no cover
    cli()
