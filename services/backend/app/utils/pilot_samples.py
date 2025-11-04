from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Sequence
import random

_STATUSES = ("invited", "contacted", "onboarding", "active")
_CHANNELS = ("web", "mobile", "wechat", "email")
_LOCALES = ("zh-CN", "zh-TW", "en-US")
_SOURCES = ("referral", "social", "webinar", "partner")
_TAGS = ("anxiety", "sleep", "stress", "work", "relationships", "mindfulness")
_SCENARIOS = ("guided-chat", "voice-journal", "therapist-match", "journey-review")
_ENVIRONMENTS = ("staging", "pilot", "qa")
_PLATFORMS = ("ios", "android", "web")
_ISSUE_TITLES = (
    "Chat transcript failed to load",
    "Voice capture stalled mid-session",
    "Therapist recommendations slow to populate",
    "Summary spotlight missing key insight",
    "Notification preferences reset unexpectedly",
)
_ISSUE_NOTES = (
    "Observed during guided breathing scene.",
    "Reproduced twice when switching locales.",
    "User toggled TTS before issue surfaced.",
    "Impacts pilot participants using mid-range Android devices.",
    "Suspect caching regression after latest deploy.",
)
_FACILITATORS = ("rankang", "li.na", "alex.chen", "zhang.qi")
_DEVICES = ("iPhone 14", "Pixel 7", "OnePlus 11", "iPad Mini", "Galaxy S23")


@dataclass(slots=True)
class PilotSampleBundle:
    """Container for generated pilot cohort sample data."""

    participants: list[dict[str, str]]
    feedback: list[dict[str, object]]
    uat_sessions: list[dict[str, object]]


def _ensure_rng(rng: random.Random | None, seed: int | None) -> random.Random:
    if rng is not None:
        return rng
    if seed is None:
        seed = int(datetime.now(timezone.utc).timestamp())
    return random.Random(seed)


def _isoformat(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def generate_participant_samples(
    count: int,
    *,
    cohort: str,
    seed: int | None = None,
    rng: random.Random | None = None,
    anchor_time: datetime | None = None,
) -> list[dict[str, str]]:
    """Create participant rows matching the pilot cohort CSV schema."""
    if count <= 0:
        return []

    rng = _ensure_rng(rng, seed)
    if anchor_time is not None:
        anchor = anchor_time
    elif seed is not None:
        anchor = datetime(2025, 1, 15, tzinfo=timezone.utc)
    else:
        anchor = datetime.now(timezone.utc)
    rows: list[dict[str, str]] = []
    base_time = anchor - timedelta(days=10)

    for index in range(1, count + 1):
        alias = f"{cohort}-{index:03d}"
        email = f"{alias.replace('-', '.')}@example.com"
        phone = f"+8613800{index:05d}"
        status = rng.choice(_STATUSES)
        channel = rng.choice(_CHANNELS)
        locale = rng.choice(_LOCALES)
        source = rng.choice(_SOURCES)
        consent = rng.random() > 0.35
        tags = rng.sample(_TAGS, k=rng.randint(1, min(3, len(_TAGS))))

        invite_offset = rng.uniform(0, 5)
        invite_sent_at = base_time - timedelta(days=invite_offset)
        onboarded_offset = invite_offset - rng.uniform(0, 2)
        onboarded_at = (
            invite_sent_at + timedelta(days=onboarded_offset)
            if onboarded_offset > 0.5
            else None
        )
        last_contacted_at = (
            onboarded_at + timedelta(days=rng.uniform(0, 3))
            if onboarded_at
            else None
        )

        metadata = {
            "preferred_contact": rng.choice(("email", "phone", "wechat")),
            "timezone": rng.choice(("Asia/Shanghai", "Asia/Taipei", "America/Los_Angeles")),
        }

        rows.append(
            {
                "cohort": cohort,
                "alias": alias,
                "email": email,
                "phone": phone,
                "status": status,
                "channel": channel,
                "locale": locale,
                "source": source,
                "tags": "|".join(tags),
                "consent": "true" if consent else "false",
                "notes": "Sample participant generated for UAT dry run.",
                "metadata": json.dumps(metadata, ensure_ascii=False),
                "invite_sent_at": _isoformat(invite_sent_at),
                "onboarded_at": _isoformat(onboarded_at) if onboarded_at else "",
                "last_contacted_at": _isoformat(last_contacted_at) if last_contacted_at else "",
            }
        )

    return rows


def generate_feedback_samples(
    count: int,
    *,
    cohort: str,
    participants: Sequence[dict[str, str]],
    seed: int | None = None,
    rng: random.Random | None = None,
    anchor_time: datetime | None = None,
) -> list[dict[str, object]]:
    """Create pilot feedback records aligned with PilotFeedbackCreate schema."""
    if count <= 0:
        return []

    rng = _ensure_rng(rng, seed)

    def _score(base: float) -> int:
        value = base + rng.uniform(-1.5, 1.5)
        return int(min(max(round(value), 1), 5))

    aliases = [row["alias"] for row in participants] or [f"{cohort}-demo"]
    if anchor_time is not None:
        anchor = anchor_time
    elif seed is not None:
        anchor = datetime(2025, 1, 18, tzinfo=timezone.utc)
    else:
        anchor = datetime.now(timezone.utc)
    base_time = anchor - timedelta(days=3)
    entries: list[dict[str, object]] = []

    for index in range(1, count + 1):
        alias = rng.choice(aliases)
        channel = rng.choice(_CHANNELS)
        scenario = rng.choice(_SCENARIOS)
        severity = rng.choice(("low", "medium", "high", None))
        tags = rng.sample(_TAGS, k=rng.randint(1, min(4, len(_TAGS))))
        follow_up_needed = rng.random() > 0.6
        submitted_at = base_time + timedelta(hours=index * 4)

        entries.append(
            {
                "cohort": cohort,
                "role": rng.choice(("participant", "facilitator", "observer")),
                "channel": channel,
                "scenario": scenario,
                "participant_alias": alias,
                "contact_email": f"{alias.replace('-', '.')}@example.com",
                "sentiment_score": _score(4.2),
                "trust_score": _score(4.0),
                "usability_score": _score(3.8),
                "severity": severity,
                "tags": tags,
                "highlights": "Sample highlight captured during mock session.",
                "blockers": (
                    "Voice playback interrupted when switching locales."
                    if follow_up_needed
                    else None
                ),
                "follow_up_needed": follow_up_needed,
                "metadata": {
                    "submitted_at": _isoformat(submitted_at),
                    "sample": True,
                },
            }
        )
    return entries


def generate_uat_session_samples(
    count: int,
    *,
    cohort: str,
    participants: Sequence[dict[str, str]],
    seed: int | None = None,
    rng: random.Random | None = None,
    anchor_time: datetime | None = None,
) -> list[dict[str, object]]:
    """Create pilot UAT session entries aligned with PilotUATSessionCreate schema."""
    if count <= 0:
        return []

    rng = _ensure_rng(rng, seed)
    aliases = [row["alias"] for row in participants] or [f"{cohort}-demo"]
    entries: list[dict[str, object]] = []
    if anchor_time is not None:
        anchor = anchor_time
    elif seed is not None:
        anchor = datetime(2025, 1, 20, tzinfo=timezone.utc)
    else:
        anchor = datetime.now(timezone.utc)
    base_time = anchor - timedelta(days=2)

    for index in range(1, count + 1):
        alias = rng.choice(aliases)
        facilitator = rng.choice(_FACILITATORS)
        scenario = rng.choice(_SCENARIOS)
        environment = rng.choice(_ENVIRONMENTS)
        platform = rng.choice(_PLATFORMS)
        device = rng.choice(_DEVICES)
        session_date = base_time + timedelta(hours=index * 3)

        issue_count = rng.randint(0, 2)
        issues = []
        if issue_count:
            titles = rng.sample(_ISSUE_TITLES, k=issue_count)
            for title in titles:
                issues.append(
                    {
                        "title": title,
                        "severity": rng.choice(("low", "medium", "high")),
                        "notes": rng.choice(_ISSUE_NOTES),
                    }
                )

        action_items = []
        if rng.random() > 0.5:
            action_items.append("Reproduce on production-like environment")
        if rng.random() > 0.7:
            action_items.append("Schedule follow-up session with participant")

        entries.append(
            {
                "cohort": cohort,
                "participant_alias": alias,
                "session_date": _isoformat(session_date),
                "facilitator": facilitator,
                "scenario": scenario,
                "environment": environment,
                "platform": platform,
                "device": device,
                "satisfaction_score": rng.randint(3, 5),
                "trust_score": rng.randint(2, 5),
                "highlights": "Participant completed onboarding without guidance.",
                "blockers": issues[0]["title"] if issues else None,
                "notes": "Sample session generated to unblock UAT dry runs.",
                "issues": issues,
                "action_items": action_items,
                "metadata": {
                    "captured_at": _isoformat(session_date + timedelta(minutes=5)),
                    "sample": True,
                },
            }
        )

    return entries


def create_pilot_sample_bundle(
    *,
    cohort: str,
    participant_count: int = 10,
    feedback_count: int = 14,
    uat_session_count: int = 8,
    seed: int | None = None,
) -> PilotSampleBundle:
    """Create a cohesive set of pilot cohort sample data."""
    rng = _ensure_rng(None, seed)
    if seed is not None:
        anchor_time = datetime(2025, 1, 15, tzinfo=timezone.utc)
    else:
        anchor_time = datetime.now(timezone.utc)
    participants = generate_participant_samples(
        participant_count,
        cohort=cohort,
        rng=rng,
        anchor_time=anchor_time,
    )
    feedback = generate_feedback_samples(
        feedback_count,
        cohort=cohort,
        participants=participants,
        rng=rng,
        anchor_time=anchor_time,
    )
    uat_sessions = generate_uat_session_samples(
        uat_session_count,
        cohort=cohort,
        participants=participants,
        rng=rng,
        anchor_time=anchor_time,
    )
    return PilotSampleBundle(participants=participants, feedback=feedback, uat_sessions=uat_sessions)


def write_sample_bundle(bundle: PilotSampleBundle, *, output_dir: Path, overwrite: bool = False) -> list[Path]:
    """Persist the sample bundle to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    participants_path = output_dir / "participants.csv"
    feedback_path = output_dir / "feedback.jsonl"
    sessions_path = output_dir / "uat_sessions.jsonl"

    if not overwrite:
        for path in (participants_path, feedback_path, sessions_path):
            if path.exists():
                raise FileExistsError(f"{path} already exists. Use overwrite=True to replace it.")

    import csv

    with participants_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "cohort",
                "alias",
                "email",
                "phone",
                "status",
                "channel",
                "locale",
                "source",
                "tags",
                "consent",
                "notes",
                "metadata",
                "invite_sent_at",
                "onboarded_at",
                "last_contacted_at",
            ],
        )
        writer.writeheader()
        writer.writerows(bundle.participants)

    for path, payloads in ((feedback_path, bundle.feedback), (sessions_path, bundle.uat_sessions)):
        with path.open("w", encoding="utf-8") as handle:
            for entry in payloads:
                handle.write(json.dumps(entry, ensure_ascii=False))
                handle.write("\n")

    return [participants_path, feedback_path, sessions_path]
