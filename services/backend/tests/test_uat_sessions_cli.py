from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.pilot_uat import (
    PilotUATGroupSummary,
    PilotUATIssue,
    PilotUATIssueSummary,
    PilotUATSessionResponse,
    PilotUATSessionSummary,
)
from scripts.uat_sessions import render_markdown_digest


def _sample_session() -> PilotUATSessionResponse:
    return PilotUATSessionResponse(
        id=uuid4(),
        cohort="pilot-2025w4",
        participant_alias="participants-01",
        participant_id=uuid4(),
        session_date=datetime(2025, 1, 15, 9, 30, tzinfo=timezone.utc),
        facilitator="qa-lead",
        scenario="chat-session",
        environment="qa",
        platform="mobile",
        device="Pixel 6a",
        satisfaction_score=4,
        trust_score=3,
        highlights="Voice playback feels natural.",
        blockers="Summary delay when switching networks.",
        notes="Participant noted minor UI lag.",
        issues=[
            PilotUATIssue(title="Latency spike", severity="high", notes="After summary refresh"),
            PilotUATIssue(title="UI jitter", severity="medium", notes=None),
        ],
        action_items=["Review caching strategy", "Audit animation performance"],
        metadata={"build": "qa-2025-01-14"},
        created_at=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
        updated_at=datetime(2025, 1, 15, 10, 5, tzinfo=timezone.utc),
    )


def test_render_markdown_digest_with_data() -> None:
    summary = PilotUATSessionSummary(
        total_sessions=2,
        distinct_participants=2,
        average_satisfaction=4.5,
        average_trust=3.5,
        sessions_with_blockers=1,
        issues_by_severity=[
            PilotUATIssueSummary(severity="high", count=1),
            PilotUATIssueSummary(severity="medium", count=1),
        ],
        sessions_by_platform=[
            PilotUATGroupSummary(
                key="mobile",
                total=2,
                average_satisfaction=4.5,
                average_trust=3.5,
            )
        ],
        sessions_by_environment=[
            PilotUATGroupSummary(
                key="qa",
                total=2,
                average_satisfaction=4.5,
                average_trust=3.5,
            )
        ],
    )

    digest = render_markdown_digest(summary, [_sample_session()])

    assert "Total sessions: **2**" in digest
    assert "| high | 1 |" in digest
    assert "| mobile | 2 | 4.50 | 3.50 |" in digest
    assert "### 2025-01-15 09:30 UTC" in digest
    assert "Latency spike" in digest
    assert "Action Items: Review caching strategy, Audit animation performance" in digest


def test_render_markdown_digest_with_no_data() -> None:
    summary = PilotUATSessionSummary(
        total_sessions=0,
        distinct_participants=0,
        average_satisfaction=None,
        average_trust=None,
        sessions_with_blockers=0,
        issues_by_severity=[],
        sessions_by_platform=[],
        sessions_by_environment=[],
    )

    digest = render_markdown_digest(summary, [])

    assert "No pilot UAT sessions have been recorded yet." in digest
    assert "_No issues logged yet._" in digest
    assert "_No data available._" in digest
    assert "_No sessions to display._" in digest
