"""Run an end-to-end pilot UAT dry run using generated or recorded samples.

This helper script wires together the pilot cohort roster, structured feedback,
and UAT session logging flows so product and research teams can validate the
instrumentation before inviting real participants. It can optionally generate a
synthetic sample bundle, import the rows into the local database, and emit a
Markdown report summarizing the resulting insights (participant funnel,
feedback sentiment, backlog hotspots, etc.).
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import delete

from app.core.database import get_session_factory, init_database
from app.models import PilotCohortParticipant, PilotFeedback, PilotUATSession
from app.schemas.feedback import (
    PilotFeedbackCreate,
    PilotFeedbackFilters,
    PilotFeedbackSummary,
)
from app.schemas.pilot_cohort import (
    PilotParticipantCreate,
    PilotParticipantFilters,
    PilotParticipantStatus,
    PilotParticipantSummary,
)
from app.schemas.pilot_uat import (
    PilotUATIssue,
    PilotUATSessionCreate,
    PilotUATSessionFilters,
    PilotUATSessionSummary,
    PilotUATBacklogItem,
)
from app.services.feedback import PilotFeedbackService
from app.services.pilot_cohort import PilotCohortService
from app.services.pilot_uat import PilotUATService
from app.utils.pilot_samples import (
    PilotSampleBundle,
    create_pilot_sample_bundle,
    write_sample_bundle,
)


PARTICIPANTS_FILE = "participants.csv"
FEEDBACK_FILE = "feedback.jsonl"
UAT_SESSIONS_FILE = "uat_sessions.jsonl"


@dataclass(slots=True)
class IngestStats:
    participants: int = 0
    feedback: int = 0
    uat_sessions: int = 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mindwell-uat-dry-run",
        description="Populate pilot cohort tables with sample data and emit a Markdown summary.",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        help="Database URL to use for the dry run (overrides DATABASE_URL env var).",
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Run Alembic migrations before importing data (default: off).",
    )
    parser.add_argument(
        "--cohort",
        default="pilot-demo",
        help="Cohort identifier applied to generated/imported records.",
    )
    parser.add_argument(
        "--sample-dir",
        type=Path,
        default=Path("./pilot_samples"),
        help="Directory containing participant/feedback/UAT sample files.",
    )
    parser.add_argument(
        "--generate-samples",
        action="store_true",
        help="Generate a fresh synthetic sample bundle before import.",
    )
    parser.add_argument(
        "--participants",
        type=int,
        default=12,
        help="Number of sample participants to generate (when --generate-samples is used).",
    )
    parser.add_argument(
        "--feedback",
        type=int,
        default=18,
        help="Number of sample feedback entries to generate (when --generate-samples is used).",
    )
    parser.add_argument(
        "--uat-sessions",
        type=int,
        default=10,
        help="Number of sample UAT sessions to generate (when --generate-samples is used).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional RNG seed to make generated samples deterministic.",
    )
    parser.add_argument(
        "--overwrite-samples",
        action="store_true",
        help="Allow the script to overwrite existing sample files when generating new ones.",
    )
    parser.add_argument(
        "--purge-existing",
        action="store_true",
        help="Delete existing pilot data for the cohort before importing the sample bundle.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=Path("./pilot_uat_dry_run_report.md"),
        help="Where to write the Markdown summary (default: ./pilot_uat_dry_run_report.md).",
    )
    return parser


def parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def parse_metadata(value: object) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return {}
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return {"raw": stripped}
    return {"raw": value}


def parse_tags(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    return [item.strip() for item in text.split("|") if item.strip()]


def load_sample_bundle(sample_dir: Path) -> PilotSampleBundle:
    participants_path = sample_dir / PARTICIPANTS_FILE
    feedback_path = sample_dir / FEEDBACK_FILE
    sessions_path = sample_dir / UAT_SESSIONS_FILE

    if not participants_path.exists() or not feedback_path.exists() or not sessions_path.exists():
        missing = [
            str(path)
            for path in (participants_path, feedback_path, sessions_path)
            if not path.exists()
        ]
        raise FileNotFoundError(
            f"Sample bundle is incomplete; missing files: {', '.join(missing)}"
        )

    with participants_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        participants = [dict(row) for row in reader]

    feedback: list[dict[str, Any]] = []
    with feedback_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            feedback.append(json.loads(stripped))

    sessions: list[dict[str, Any]] = []
    with sessions_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            sessions.append(json.loads(stripped))

    return PilotSampleBundle(participants=participants, feedback=feedback, uat_sessions=sessions)


async def purge_cohort_data(cohort: str) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(delete(PilotUATSession).where(PilotUATSession.cohort == cohort))
        await session.execute(delete(PilotFeedback).where(PilotFeedback.cohort == cohort))
        await session.execute(delete(PilotCohortParticipant).where(PilotCohortParticipant.cohort == cohort))
        await session.commit()


def to_participant_payload(row: dict[str, Any], cohort: str) -> PilotParticipantCreate:
    tags = parse_tags(row.get("tags") or row.get("tag_list"))
    metadata = parse_metadata(row.get("metadata"))
    status_text = str(row.get("status") or PilotParticipantStatus.INVITED.value).strip().lower()
    try:
        status = PilotParticipantStatus(status_text)
    except ValueError:
        status = PilotParticipantStatus.INVITED
    return PilotParticipantCreate(
        cohort=row.get("cohort") or cohort,
        participant_alias=row.get("participant_alias") or row.get("alias"),
        contact_email=row.get("contact_email") or row.get("email"),
        contact_phone=row.get("contact_phone") or row.get("phone"),
        channel=row.get("channel") or "web",
        locale=row.get("locale") or "zh-CN",
        status=status,
        source=row.get("source"),
        tags=tags,
        invite_sent_at=parse_datetime(row.get("invite_sent_at")),
        onboarded_at=parse_datetime(row.get("onboarded_at")),
        last_contacted_at=parse_datetime(row.get("last_contacted_at")),
        consent_received=parse_bool(row.get("consent") or row.get("consent_received")),
        notes=row.get("notes"),
        metadata=metadata,
    )


def to_feedback_payload(entry: dict[str, Any], cohort: str) -> PilotFeedbackCreate:
    metadata = parse_metadata(entry.get("metadata"))
    return PilotFeedbackCreate(
        cohort=entry.get("cohort") or cohort,
        role=entry.get("role") or "participant",
        channel=entry.get("channel") or "web",
        scenario=entry.get("scenario"),
        participant_alias=entry.get("participant_alias"),
        contact_email=entry.get("contact_email"),
        sentiment_score=int(entry.get("sentiment_score", 3)),
        trust_score=int(entry.get("trust_score", 3)),
        usability_score=int(entry.get("usability_score", 3)),
        severity=entry.get("severity"),
        tags=parse_tags(entry.get("tags")),
        highlights=entry.get("highlights"),
        blockers=entry.get("blockers"),
        follow_up_needed=parse_bool(entry.get("follow_up_needed")),
        metadata=metadata,
    )


def to_uat_payload(
    entry: dict[str, Any],
    cohort: str,
    alias_map: dict[str, Any],
) -> PilotUATSessionCreate:
    issues_data = entry.get("issues") or []
    issues = [PilotUATIssue(**issue) if not isinstance(issue, PilotUATIssue) else issue for issue in issues_data]
    action_items = [str(item).strip() for item in entry.get("action_items") or [] if str(item).strip()]
    alias = entry.get("participant_alias")
    participant_id = alias_map.get(str(alias).strip().lower()) if alias else None

    return PilotUATSessionCreate(
        cohort=entry.get("cohort") or cohort,
        participant_alias=alias,
        participant_id=participant_id,
        session_date=parse_datetime(entry.get("session_date")),
        facilitator=entry.get("facilitator"),
        scenario=entry.get("scenario"),
        environment=entry.get("environment"),
        platform=entry.get("platform"),
        device=entry.get("device"),
        satisfaction_score=int(entry.get("satisfaction_score", 3)),
        trust_score=int(entry.get("trust_score")) if entry.get("trust_score") is not None else None,
        highlights=entry.get("highlights"),
        blockers=entry.get("blockers"),
        notes=entry.get("notes"),
        issues=issues,
        action_items=action_items,
        metadata=parse_metadata(entry.get("metadata")),
    )


async def ingest_sample_bundle(
    bundle: PilotSampleBundle,
    cohort: str,
) -> IngestStats:
    stats = IngestStats()
    session_factory = get_session_factory()
    async with session_factory() as session:
        cohort_service = PilotCohortService(session)
        feedback_service = PilotFeedbackService(session)
        uat_service = PilotUATService(session)

        alias_map: dict[str, Any] = {}

        for row in bundle.participants:
            payload = to_participant_payload(dict(row), cohort)
            record = await cohort_service.create_participant(payload)
            stats.participants += 1
            alias_key = (record.participant_alias or "").strip().lower()
            if alias_key:
                alias_map[alias_key] = record.id

        await session.commit()

        for entry in bundle.feedback:
            payload = to_feedback_payload(dict(entry), cohort)
            await feedback_service.record_feedback(payload)
            stats.feedback += 1

        await session.commit()

        for entry in bundle.uat_sessions:
            payload = to_uat_payload(dict(entry), cohort, alias_map)
            await uat_service.log_session(payload)
            stats.uat_sessions += 1

        await session.commit()

    return stats


async def generate_report(
    cohort: str,
    report_path: Path,
) -> str:
    session_factory = get_session_factory()
    async with session_factory() as session:
        cohort_service = PilotCohortService(session)
        feedback_service = PilotFeedbackService(session)
        uat_service = PilotUATService(session)

        participant_summary = await cohort_service.summarize_participants(
            PilotParticipantFilters(cohort=cohort)
        )
        feedback_summary = await feedback_service.summarize_feedback(
            PilotFeedbackFilters(cohort=cohort)
        )
        uat_summary = await uat_service.summarize_sessions(
            PilotUATSessionFilters(cohort=cohort)
        )
        backlog = await uat_service.prioritize_backlog(
            PilotUATSessionFilters(cohort=cohort)
        )

    markdown = build_markdown_report(
        cohort=cohort,
        participant_summary=participant_summary,
        feedback_summary=feedback_summary,
        uat_summary=uat_summary,
        backlog_items=backlog.items,
    )
    report_path.write_text(markdown, encoding="utf-8")
    return markdown


def build_markdown_report(
    *,
    cohort: str,
    participant_summary: PilotParticipantSummary,
    feedback_summary: PilotFeedbackSummary,
    uat_summary: PilotUATSessionSummary,
    backlog_items: Iterable[PilotUATBacklogItem],
) -> str:
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _table(rows: list[tuple[str, str]]) -> str:
        header = "| Metric | Value |\n| --- | --- |\n"
        body = "\n".join(f"| {label} | {value} |" for label, value in rows)
        return header + body

    sections: list[str] = [
        "# MindWell Pilot UAT Dry Run Report",
        f"- Cohort: `{cohort}`",
        f"- Generated: `{timestamp}`",
        "",
        "## Participant Funnel",
        _table(
            [
                ("Total participants", str(participant_summary.total)),
                ("Consent received", str(participant_summary.with_consent)),
                ("Consent pending", str(participant_summary.without_consent)),
            ]
        ),
    ]

    if participant_summary.by_status:
        sections.append("")
        sections.append("### Participants by Status")
        sections.append("| Status | Count |")
        sections.append("| --- | --- |")
        sections.extend(
            f"| {bucket.key} | {bucket.total} |" for bucket in participant_summary.by_status
        )

    if participant_summary.top_tags:
        sections.append("")
        sections.append("### Top Participant Tags")
        sections.append("| Tag | Count |")
        sections.append("| --- | --- |")
        sections.extend(
            f"| {bucket.key} | {bucket.total} |" for bucket in participant_summary.top_tags
        )

    sections.extend(
        [
            "",
            "## Feedback Sentiment",
            _table(
                [
                    ("Total feedback entries", str(feedback_summary.total_entries)),
                    ("Average sentiment", str(feedback_summary.average_sentiment)),
                    ("Average trust", str(feedback_summary.average_trust)),
                    ("Average usability", str(feedback_summary.average_usability)),
                    ("Follow-up needed", str(feedback_summary.follow_up_needed)),
                ]
            ),
        ]
    )

    if feedback_summary.top_tags:
        sections.append("")
        sections.append("### Feedback Themes")
        sections.append("| Tag | Occurrences |")
        sections.append("| --- | --- |")
        sections.extend(
            f"| {tag.tag} | {tag.count} |" for tag in feedback_summary.top_tags
        )

    sections.extend(
        [
            "",
            "## UAT Session Overview",
            _table(
                [
                    ("Total sessions", str(uat_summary.total_sessions)),
                    ("Distinct participants", str(uat_summary.distinct_participants)),
                    ("Average satisfaction", str(uat_summary.average_satisfaction)),
                    ("Average trust", str(uat_summary.average_trust)),
                    ("Sessions with blockers", str(uat_summary.sessions_with_blockers)),
                ]
            ),
        ]
    )

    if uat_summary.issues_by_severity:
        sections.append("")
        sections.append("### Issues by Severity")
        sections.append("| Severity | Count |")
        sections.append("| --- | --- |")
        sections.extend(
            f"| {issue.severity} | {issue.count} |" for issue in uat_summary.issues_by_severity
        )

    backlog_list = list(backlog_items)
    if backlog_list:
        sections.append("")
        sections.append("## Prioritized Backlog")
        for index, item in enumerate(backlog_list, start=1):
            sections.append(
                f"{index}. **{item.title}** — severity `{item.severity}` "
                f"({item.occurrences} occurrences, {item.affected_participants} participants)"
            )
            if item.action_items:
                joined = ", ".join(item.action_items)
                sections.append(f"   - Suggested actions: {joined}")
            if item.sample_notes:
                for note in item.sample_notes:
                    sections.append(f"   - Note: {note}")

    sections.append("")
    sections.append("> Generated by `mindwell-uat-dry-run`.")

    return "\n".join(sections).strip() + "\n"


async def async_main(args: argparse.Namespace) -> int:
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    if args.init_db:
        await init_database()

    if args.generate_samples:
        bundle = create_pilot_sample_bundle(
            cohort=args.cohort,
            participant_count=args.participants,
            feedback_count=args.feedback,
            uat_session_count=args.uat_sessions,
            seed=args.seed,
        )
        write_sample_bundle(
            bundle,
            output_dir=args.sample_dir,
            overwrite=args.overwrite_samples,
        )
    else:
        bundle = load_sample_bundle(args.sample_dir)

    if args.purge_existing:
        await purge_cohort_data(args.cohort)

    stats = await ingest_sample_bundle(bundle, args.cohort)
    markdown = await generate_report(args.cohort, args.report_path)

    print("Pilot UAT dry run complete:")
    print(f"  Participants imported:   {stats.participants}")
    print(f"  Feedback entries logged: {stats.feedback}")
    print(f"  UAT sessions recorded:   {stats.uat_sessions}")
    print(f"Markdown report written to {args.report_path}")
    print()
    print(markdown)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return asyncio.run(async_main(args))
    except KeyboardInterrupt:
        return 130


def cli() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(cli())
