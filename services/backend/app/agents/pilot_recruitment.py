from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import httpx

from app.core.config import AppSettings, get_settings
from app.core.database import session_scope
from app.schemas.feedback import (
    PilotParticipantCreate,
    PilotParticipantFilters,
    PilotParticipantSummary,
)
from app.services.feedback import PilotParticipantService


logger = logging.getLogger("mindwell.pilot_recruitment")


def _normalize_key(key: str) -> str:
    return (
        str(key)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def _coerce_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "t", "yes", "y"}:
        return True
    if normalized in {"0", "false", "f", "no", "n"}:
        return False
    raise ValueError(f"Unable to interpret boolean value from {value!r}")


def _parse_datetime(value: Any, field: str) -> datetime | None:
    if value in (None, "", "null"):
        return None
    if isinstance(value, datetime):
        candidate = value
    else:
        text = str(value).strip()
        try:
            candidate = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"Field '{field}' has invalid datetime value {value!r}") from exc
    if candidate.tzinfo is None:
        return candidate.replace(tzinfo=timezone.utc)
    return candidate.astimezone(timezone.utc)


def _parse_tags(value: Any, separator: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        candidates = value
    else:
        normalized = str(value).replace(";", separator)
        candidates = normalized.split(separator)
    parsed: list[str] = []
    seen: set[str] = set()
    for tag in candidates:
        text = str(tag).strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        parsed.append(text)
    return parsed


def _parse_metadata(value: Any) -> dict[str, Any]:
    if value is None or value == "":
        return {}
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Metadata payload must be JSON object: {value!r}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Metadata payload must decode to a JSON object.")
    return parsed


def _load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Candidate source file {path} does not exist.")

    suffix = path.suffix.lower()
    if suffix in {".json", ".jsonl"}:
        if suffix == ".jsonl":
            records: list[dict[str, Any]] = []
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON on line {line_no} of {path}: {exc}") from exc
                if not isinstance(payload, dict):
                    raise ValueError(f"Expected object per line in {path}, found {type(payload)!r}")
                records.append(payload)
            return records

        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ("participants", "items", "records", "data"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        raise ValueError(f"Unsupported JSON schema in {path}.")

    if suffix in {".csv", ".tsv"}:
        delimiter = "\t" if suffix == ".tsv" else ","
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            return [dict(row) for row in reader]

    raise ValueError(f"Unsupported candidate file format for {path}. Expected JSON/JSONL/CSV/TSV.")


def _argparse_bool(value: str) -> bool:
    try:
        return _coerce_bool(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


@dataclass(slots=True)
class ImportResult:
    total_rows: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    dry_run: bool = False


class PilotRecruitmentAgent:
    """Manage pilot participant imports and summarize recruitment health."""

    def __init__(self, service: PilotParticipantService):
        self._service = service

    async def import_candidates(
        self,
        records: Iterable[dict[str, Any]],
        *,
        cohort: str | None,
        default_status: str,
        default_channel: str,
        tag_separator: str = ",",
        dry_run: bool = False,
    ) -> ImportResult:
        result = ImportResult(dry_run=dry_run)
        for index, raw in enumerate(records, start=1):
            result.total_rows += 1
            try:
                payload = self._build_payload(
                    raw,
                    cohort=cohort,
                    default_status=default_status,
                    default_channel=default_channel,
                    tag_separator=tag_separator,
                )
            except ValueError as exc:
                result.skipped += 1
                result.errors.append(f"row {index}: {exc}")
                continue

            if dry_run:
                existing = (
                    await self._service.find_participant_by_cohort_email(
                        payload.cohort, payload.contact_email
                    )
                    if payload.contact_email
                    else None
                )
                if existing:
                    result.updated += 1
                else:
                    result.created += 1
                continue

            try:
                _, created = await self._service.upsert_participant(payload)
            except ValueError as exc:
                result.skipped += 1
                result.errors.append(f"row {index}: {exc}")
                continue

            if created:
                result.created += 1
            else:
                result.updated += 1

        return result

    async def generate_report(
        self,
        filters: PilotParticipantFilters | None = None,
    ) -> PilotParticipantSummary:
        return await self._service.summarize_participants(filters)

    def _build_payload(
        self,
        record: dict[str, Any],
        *,
        cohort: str | None,
        default_status: str,
        default_channel: str,
        tag_separator: str,
    ) -> PilotParticipantCreate:
        normalized = {
            _normalize_key(key): value for key, value in record.items() if isinstance(key, str)
        }

        target_cohort = _coerce_str(normalized.get("cohort")) or _coerce_str(cohort)
        if not target_cohort:
            raise ValueError("Cohort is required for pilot participants.")

        status = _coerce_str(normalized.get("status")) or _coerce_str(default_status)
        if not status:
            raise ValueError("Status is required when importing pilot participants.")

        channel = _coerce_str(normalized.get("channel")) or _coerce_str(default_channel)
        if not channel:
            raise ValueError("Channel is required when importing pilot participants.")

        contact_email = _coerce_str(normalized.get("contact_email"))
        contact_phone = _coerce_str(normalized.get("contact_phone"))
        if not contact_email and not contact_phone:
            raise ValueError("Either contact email or phone must be provided for follow-up.")

        requires_follow_up = normalized.get("requires_follow_up")
        try:
            follow_up_flag = _coerce_bool(requires_follow_up)
        except ValueError:
            follow_up_flag = False

        metadata = {}
        if "metadata" in normalized:
            metadata = _parse_metadata(normalized.get("metadata"))

        invited_at = _parse_datetime(normalized.get("invited_at"), "invited_at")
        consent_signed_at = _parse_datetime(
            normalized.get("consent_signed_at"), "consent_signed_at"
        )
        onboarded_at = _parse_datetime(normalized.get("onboarded_at"), "onboarded_at")
        last_contact_at = _parse_datetime(normalized.get("last_contact_at"), "last_contact_at")

        return PilotParticipantCreate(
            cohort=target_cohort,
            full_name=_coerce_str(normalized.get("full_name")),
            preferred_name=_coerce_str(normalized.get("preferred_name")),
            contact_email=contact_email,
            contact_phone=contact_phone,
            channel=channel,
            locale=_coerce_str(normalized.get("locale")) or "zh-CN",
            timezone=_coerce_str(normalized.get("timezone")),
            organization=_coerce_str(normalized.get("organization")),
            status=status,
            requires_follow_up=follow_up_flag,
            invited_at=invited_at,
            consent_signed_at=consent_signed_at,
            onboarded_at=onboarded_at,
            last_contact_at=last_contact_at,
            follow_up_notes=_coerce_str(normalized.get("follow_up_notes")),
            tags=_parse_tags(normalized.get("tags"), tag_separator),
            metadata=metadata,
        )


async def _notify_summary(summary: PilotParticipantSummary, settings: AppSettings) -> None:
    if not settings.alert_webhook_url:
        logger.warning("Alert webhook URL not configured; skipping notification.")
        return

    webhook = settings.alert_webhook_url.get_secret_value()
    lines = [
        f"*Pilot Recruitment Snapshot* — cohort `{summary.cohort or 'all'}`",
        f"Total participants: {summary.total}",
        f"Pending invites: {summary.pending_invites} | Requires follow-up: {summary.requires_follow_up}",
        f"Invited: {summary.invited} | Consented: {summary.consented} | Onboarded: {summary.onboarded}",
        f"Contact-ready profiles: {summary.with_contact_methods}",
    ]
    if summary.status_breakdown:
        breakdown = ", ".join(f"{name}: {count}" for name, count in summary.status_breakdown.items())
        lines.append(f"Status counts — {breakdown}")
    if summary.tag_totals:
        top_tags = list(summary.tag_totals.items())[:3]
        tag_line = ", ".join(f"{tag} ({count})" for tag, count in top_tags)
        lines.append(f"Top tags — {tag_line}")
    if summary.last_activity_at:
        lines.append(f"Last activity at: {summary.last_activity_at.isoformat()}")

    payload: dict[str, Any] = {"text": "\n".join(lines)}
    if settings.alert_channel:
        payload["channel"] = settings.alert_channel

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(webhook, json=payload)
        response.raise_for_status()
    logger.info("Dispatched pilot recruitment summary notification.")


async def _run_import(args: argparse.Namespace) -> None:
    records = _load_records(args.path)
    async with session_scope() as session:
        service = PilotParticipantService(session)
        agent = PilotRecruitmentAgent(service)
        result = await agent.import_candidates(
            records,
            cohort=args.cohort,
            default_status=args.default_status,
            default_channel=args.default_channel,
            tag_separator=args.tag_separator,
            dry_run=args.dry_run,
        )

    mode = "dry-run" if result.dry_run else "applied"
    logger.info(
        "Pilot participant import %s complete — total=%s created=%s updated=%s skipped=%s",
        mode,
        result.total_rows,
        result.created,
        result.updated,
        result.skipped,
    )
    if result.errors:
        for message in result.errors:
            logger.warning("Import notice: %s", message)


async def _run_report(args: argparse.Namespace) -> None:
    settings = get_settings()
    filters = PilotParticipantFilters(
        cohort=args.cohort,
        status=args.status,
        requires_follow_up=args.requires_follow_up,
        tag=args.tag,
    )
    async with session_scope() as session:
        service = PilotParticipantService(session)
        agent = PilotRecruitmentAgent(service)
        summary = await agent.generate_report(filters)

    payload = summary.model_dump(mode="json")
    formatted = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.json_path:
        args.json_path.write_text(formatted, encoding="utf-8")
        logger.info("Wrote pilot recruitment summary to %s", args.json_path)
    else:
        print(formatted)

    if args.notify:
        await _notify_summary(summary, settings)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")

    parser = argparse.ArgumentParser(
        prog="mindwell-pilot-recruitment",
        description="Manage pilot participant imports and generate recruitment summaries.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser(
        "import",
        help="Import pilot participant candidates from CSV/TSV/JSON data sources.",
    )
    import_parser.add_argument(
        "path",
        type=Path,
        help="Path to the candidate dataset (CSV, TSV, JSON, or JSONL).",
    )
    import_parser.add_argument(
        "--cohort",
        default=None,
        help="Optional cohort slug to apply when rows do not specify one.",
    )
    import_parser.add_argument(
        "--default-status",
        default="prospect",
        help="Status to apply when a row omits the status column (default: prospect).",
    )
    import_parser.add_argument(
        "--default-channel",
        default="web",
        help="Channel to apply when a row omits the channel column (default: web).",
    )
    import_parser.add_argument(
        "--tag-separator",
        default=",",
        help="Delimiter used when parsing tag strings (default: comma).",
    )
    import_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate input records and report changes without modifying the database.",
    )

    report_parser = subparsers.add_parser(
        "report",
        help="Generate a recruitment summary for the specified cohort filters.",
    )
    report_parser.add_argument(
        "--cohort",
        default=None,
        help="Optional cohort slug to filter by.",
    )
    report_parser.add_argument(
        "--status",
        default=None,
        help="Optional participant status filter.",
    )
    report_parser.add_argument(
        "--requires-follow-up",
        type=_argparse_bool,
        default=None,
        help="Filter by follow-up requirement (true/false).",
    )
    report_parser.add_argument(
        "--tag",
        default=None,
        help="Filter by a single participant tag.",
    )
    report_parser.add_argument(
        "--json",
        dest="json_path",
        type=Path,
        default=None,
        help="Optional path to write the summary as JSON instead of printing.",
    )
    report_parser.add_argument(
        "--notify",
        action="store_true",
        help="Send the summary to the configured alert webhook when set.",
    )

    args = parser.parse_args()
    if args.command == "import":
        asyncio.run(_run_import(args))
    elif args.command == "report":
        asyncio.run(_run_report(args))
    else:
        parser.error("Unsupported command.")


if __name__ == "__main__":
    main()
