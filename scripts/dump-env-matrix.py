#!/usr/bin/env python3
"""
Generate an audit-friendly CSV describing MindWell environment variables.

The data mirrors the matrix documented in ENVS.md so that Compliance and
platform teams can track rotation cadences from a machine-readable source.
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class EnvRecord:
    variable: str
    required_environments: str
    source_of_truth: str
    rotation_owner: str
    rotation_cadence: str
    automation_hooks: str


MATRIX: tuple[EnvRecord, ...] = (
    EnvRecord(
        variable="JWT_SECRET_KEY",
        required_environments="dev, staging, prod",
        source_of_truth="Azure Key Vault kv-mindwell-<env> secret jwt-secret-key",
        rotation_owner="Platform Engineering",
        rotation_cadence="Every 6 months or after incident",
        automation_hooks="GitHub Actions rotate-jwt-secret.yml (Key Vault + Secrets Manager sync)",
    ),
    EnvRecord(
        variable="DATABASE_URL",
        required_environments="dev, staging, prod",
        source_of_truth="Azure Key Vault kv-mindwell-<env> secret postgres-connection-string",
        rotation_owner="Data Platform",
        rotation_cadence="Quarterly after credential rotation",
        automation_hooks="Terraform output -> Azure DevOps job running az postgres credential rotate",
    ),
    EnvRecord(
        variable="AZURE_OPENAI_API_KEY",
        required_environments="staging, prod",
        source_of_truth="Azure Key Vault secret azure-openai-api-key",
        rotation_owner="Applied AI Team",
        rotation_cadence="Every 90 days",
        automation_hooks="Summary Scheduler Agent refreshes cache when Key Vault version changes",
    ),
    EnvRecord(
        variable="AZURE_OPENAI_DEPLOYMENT",
        required_environments="staging, prod",
        source_of_truth="Terraform variable azure_openai_deployment",
        rotation_owner="Applied AI Team",
        rotation_cadence="On model upgrade",
        automation_hooks="Terraform plan gate requires AI sign-off",
    ),
    EnvRecord(
        variable="AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT",
        required_environments="staging, prod",
        source_of_truth="Terraform variable azure_openai_embeddings_deployment",
        rotation_owner="Applied AI Team",
        rotation_cadence="On embeddings upgrade",
        automation_hooks="Terraform plan gate requires AI sign-off",
    ),
    EnvRecord(
        variable="S3_CONVERSATION_LOGS_BUCKET",
        required_environments="dev, staging, prod",
        source_of_truth="Terraform output conversation_logs_bucket",
        rotation_owner="Platform Engineering",
        rotation_cadence="Not applicable (resource identifier)",
        automation_hooks="Monitoring Agent verifies encryption setting nightly",
    ),
    EnvRecord(
        variable="S3_SUMMARIES_BUCKET",
        required_environments="dev, staging, prod",
        source_of_truth="Terraform output summaries_bucket",
        rotation_owner="Platform Engineering",
        rotation_cadence="Not applicable",
        automation_hooks="Summary Scheduler Agent sanity-checks bucket presence",
    ),
    EnvRecord(
        variable="S3_BUCKET_THERAPISTS",
        required_environments="dev, staging, prod",
        source_of_truth="Terraform output therapists_bucket",
        rotation_owner="Data Ops",
        rotation_cadence="Not applicable",
        automation_hooks="Data Sync Agent publishes locale-prefixed payloads",
    ),
    EnvRecord(
        variable="SMS_PROVIDER_API_KEY",
        required_environments="staging, prod",
        source_of_truth="AWS Secrets Manager mindwell/sms-provider",
        rotation_owner="Growth Engineering",
        rotation_cadence="Every 60 days",
        automation_hooks="GitHub Actions deployment job injects secret into AKS",
    ),
    EnvRecord(
        variable="GOOGLE_OAUTH_CLIENT_SECRET",
        required_environments="staging, prod",
        source_of_truth="1Password vault MindWell OAuth + Azure Key Vault replica",
        rotation_owner="Mobile Team",
        rotation_cadence="Every 180 days or after incident",
        automation_hooks="docs/security/oauth_rotation.md runbook updates Firebase + Key Vault",
    ),
    EnvRecord(
        variable="AZURE_SPEECH_KEY",
        required_environments="staging, prod",
        source_of_truth="Azure Key Vault secret azure-speech-key",
        rotation_owner="Voice Experience",
        rotation_cadence="Every 90 days",
        automation_hooks="Monitoring Agent alarms when key age exceeds 100 days",
    ),
    EnvRecord(
        variable="BEDROCK_MODEL_ID",
        required_environments="dev, staging, prod",
        source_of_truth="Terraform variable bedrock_model_id",
        rotation_owner="Platform Engineering",
        rotation_cadence="On fallback provider change",
        automation_hooks="Infra release pipeline applies Terraform",
    ),
    EnvRecord(
        variable="AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY",
        required_environments="dev (local only)",
        source_of_truth="Generated by scripts/bootstrap-local-env.sh assume-role flow",
        rotation_owner="Platform Engineering",
        rotation_cadence="When sandbox IAM user is rotated",
        automation_hooks="Bootstrap script re-requests credentials via STS",
    ),
)


def write_csv(records: Iterable[EnvRecord], handle: csv.writer) -> None:
    handle.writerow(
        [
            "variable",
            "required_environments",
            "source_of_truth",
            "rotation_owner",
            "rotation_cadence",
            "automation_hooks",
        ]
    )
    for record in records:
        handle.writerow(asdict(record).values())


def main(argv: list[str]) -> int:
    output_path = Path(argv[1]) if len(argv) > 1 else None
    if output_path:
        with output_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            write_csv(MATRIX, writer)
    else:
        writer = csv.writer(sys.stdout)
        write_csv(MATRIX, writer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
