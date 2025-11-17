from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

from app.core.database import session_scope
from app.schemas.feedback import (
    PilotFeedbackFilters,
    PilotFeedbackReport,
    PilotFeedbackInsight,
)
from app.services.feedback import PilotFeedbackService


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Failed to parse datetime '{value}'. Expected ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)."
        ) from exc


async def _generate_report(filters: PilotFeedbackFilters) -> PilotFeedbackReport:
    async with session_scope() as session:
        service = PilotFeedbackService(session)
        return await service.summarize_feedback(filters)


def _format_breakdown(title: str, mapping: dict[str, int]) -> str:
    lines = [f"### {title}"]
    if not mapping:
        lines.append("_No data available._")
        return "\n".join(lines)

    lines.append("| Key | Count |")
    lines.append("| --- | ---: |")
    for key, value in sorted(mapping.items(), key=lambda item: (-item[1], item[0])):
        label = key or "unspecified"
        lines.append(f"| {label} | {value} |")
    return "\n".join(lines)


def _format_insights(
    title: str, entries: list[PilotFeedbackInsight], attribute: str
) -> str:
    lines = [f"### {title}"]
    if not entries:
        lines.append("_No entries recorded._")
        return "\n".join(lines)

    for entry in entries:
        value = getattr(entry, attribute)
        if not value:
            continue
        alias = entry.participant_alias or entry.role
        timestamp = entry.submitted_at.isoformat()
        lines.append(
            f"- **{alias}** ({timestamp}, {entry.channel}) — {value.strip()}"
        )
    if len(lines) == 1:
        lines.append("_No entries recorded._")
    return "\n".join(lines)


def _render_markdown(report: PilotFeedbackReport) -> str:
    scorecard = report.average_scores
    lines = [
        "# Pilot Feedback Report",
        f"- Generated at: {report.generated_at.isoformat()}",
        f"- Total entries: {report.total_entries}",
        f"- Avg sentiment: {scorecard.average_sentiment} (>=4: {scorecard.tone_support_rate}%)",
        f"- Avg trust: {scorecard.average_trust} (>=4: {scorecard.trust_confidence_rate}%)",
        f"- Avg usability: {scorecard.average_usability} (>=4: {scorecard.usability_success_rate}%)",
        f"- Follow-ups needed: {report.follow_up_required}",
        "",
        _format_breakdown("Severity Breakdown", report.severity_breakdown),
        "",
        _format_breakdown("Channel Breakdown", report.channel_breakdown),
        "",
        _format_breakdown("Role Breakdown", report.role_breakdown),
    ]

    lines.append("")
    lines.append("### Top Tags")
    if not report.tag_frequency:
        lines.append("_No tags recorded._")
    else:
        for stat in report.tag_frequency:
            lines.append(f"- {stat.tag} ({stat.count})")

    lines.extend(
        [
            "",
            _format_insights("Recent Highlights", report.recent_highlights, "highlights"),
            "",
            _format_insights("Blockers & Severity Calls", report.blocker_insights, "blockers"),
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _build_filters(args: argparse.Namespace) -> PilotFeedbackFilters:
    return PilotFeedbackFilters(
        cohort=args.cohort,
        channel=args.channel,
        role=args.role,
        severity=args.severity,
        follow_up_needed=args.follow_up_needed,
        submitted_since=_parse_datetime(args.submitted_since),
        submitted_until=_parse_datetime(args.submitted_until),
        minimum_trust_score=args.minimum_trust_score,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mindwell-uat-report",
        description="Generate aggregated reports for pilot UAT feedback.",
    )
    parser.add_argument("--cohort", help="Filter by cohort tag (e.g., pilot-2025w4).")
    parser.add_argument("--channel", help="Filter by primary channel (web/mobile/etc).")
    parser.add_argument("--role", help="Filter by participant role (participant/therapist/etc).")
    parser.add_argument("--severity", help="Filter by severity label (e.g., high, blocker).")
    parser.add_argument(
        "--submitted-since",
        help="Include entries submitted at or after this ISO timestamp.",
    )
    parser.add_argument(
        "--submitted-until",
        help="Include entries submitted at or before this ISO timestamp.",
    )
    parser.add_argument(
        "--minimum-trust-score",
        type=int,
        choices=range(1, 6),
        help="Only include entries with trust score greater than or equal to this value.",
    )
    follow_group = parser.add_mutually_exclusive_group()
    follow_group.add_argument(
        "--follow-up-needed",
        dest="follow_up_needed",
        action="store_true",
        help="Only include entries requiring follow-up.",
    )
    follow_group.add_argument(
        "--no-follow-up-needed",
        dest="follow_up_needed",
        action="store_false",
        help="Only include entries that do not require follow-up.",
    )
    parser.set_defaults(follow_up_needed=None)
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format (default: markdown).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional file path for saving the report; prints to stdout if omitted.",
    )
    args = parser.parse_args()

    filters = _build_filters(args)
    report = asyncio.run(_generate_report(filters))
    if args.format == "json":
        content = json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2)
    else:
        content = _render_markdown(report)

    if args.output:
        args.output.write_text(content, encoding="utf-8")
    else:
        print(content)


if __name__ == "__main__":
    main()
