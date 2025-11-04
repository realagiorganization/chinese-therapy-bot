from __future__ import annotations

import csv
import json
import pytest

from app.utils import pilot_samples


def test_create_pilot_sample_bundle_deterministic() -> None:
    bundle_one = pilot_samples.create_pilot_sample_bundle(
        cohort="pilot-demo",
        participant_count=5,
        feedback_count=4,
        uat_session_count=3,
        seed=42,
    )
    bundle_two = pilot_samples.create_pilot_sample_bundle(
        cohort="pilot-demo",
        participant_count=5,
        feedback_count=4,
        uat_session_count=3,
        seed=42,
    )

    assert bundle_one.participants == bundle_two.participants
    assert bundle_one.feedback == bundle_two.feedback
    assert bundle_one.uat_sessions == bundle_two.uat_sessions


def test_generate_participant_samples_structure() -> None:
    participants = pilot_samples.generate_participant_samples(
        3,
        cohort="pilot-demo",
        seed=7,
    )
    assert len(participants) == 3
    for entry in participants:
        assert entry["cohort"] == "pilot-demo"
        assert entry["alias"]
        assert entry["email"].endswith("@example.com")
        assert entry["phone"].startswith("+86")
        assert entry["status"] in {"invited", "contacted", "onboarding", "active"}
        assert entry["metadata"]
        assert entry["invite_sent_at"]


def test_write_sample_bundle(tmp_path) -> None:
    bundle = pilot_samples.create_pilot_sample_bundle(
        cohort="pilot-demo",
        participant_count=2,
        feedback_count=2,
        uat_session_count=2,
        seed=100,
    )
    output_dir = tmp_path / "samples"
    paths = pilot_samples.write_sample_bundle(bundle, output_dir=output_dir, overwrite=False)

    participants_path, feedback_path, sessions_path = paths
    assert participants_path.exists()
    assert feedback_path.exists()
    assert sessions_path.exists()

    with participants_path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2

    with feedback_path.open(encoding="utf-8") as handle:
        feedback_lines = [json.loads(line) for line in handle]
    assert len(feedback_lines) == 2
    assert {entry["cohort"] for entry in feedback_lines} == {"pilot-demo"}

    with sessions_path.open(encoding="utf-8") as handle:
        session_lines = [json.loads(line) for line in handle]
    assert len(session_lines) == 2

    with pytest.raises(FileExistsError):
        pilot_samples.write_sample_bundle(bundle, output_dir=output_dir, overwrite=False)

    pilot_samples.write_sample_bundle(bundle, output_dir=output_dir, overwrite=True)
