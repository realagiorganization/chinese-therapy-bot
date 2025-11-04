"""Generate pilot cohort sample data to accelerate UAT dry runs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.utils.pilot_samples import create_pilot_sample_bundle, write_sample_bundle


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mindwell-pilot-samples",
        description="Generate pilot cohort sample data (participants, feedback, UAT sessions).",
    )
    parser.add_argument(
        "--cohort",
        default="pilot-demo",
        help="Cohort identifier embedded in generated aliases (default: pilot-demo).",
    )
    parser.add_argument(
        "--participants",
        type=int,
        default=12,
        help="Number of sample participants to create (default: 12).",
    )
    parser.add_argument(
        "--feedback",
        type=int,
        default=18,
        help="Number of feedback entries to create (default: 18).",
    )
    parser.add_argument(
        "--uat-sessions",
        type=int,
        default=10,
        help="Number of sample UAT sessions to create (default: 10).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional seed value for deterministic generation.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./pilot_samples"),
        help="Directory where sample files will be written (default: ./pilot_samples).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing files in the output directory.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.participants < 0 or args.feedback < 0 or args.uat_sessions < 0:
        raise SystemExit("Counts must be non-negative integers.")

    bundle = create_pilot_sample_bundle(
        cohort=args.cohort,
        participant_count=args.participants,
        feedback_count=args.feedback,
        uat_session_count=args.uat_sessions,
        seed=args.seed,
    )

    try:
        paths = write_sample_bundle(
            bundle,
            output_dir=args.output_dir,
            overwrite=args.overwrite,
        )
    except FileExistsError as exc:
        raise SystemExit(str(exc)) from exc

    for path in paths:
        print(f"Wrote {path}")
    return 0


def cli() -> int:
    return main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(cli())
