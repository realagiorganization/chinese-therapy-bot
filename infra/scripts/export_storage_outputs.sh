#!/usr/bin/env bash
# Extracts the AWS storage + CI runner outputs from a Terraform environment and
# writes both JSON and .env artifacts for downstream automation.
#
# Usage:
#   ./export_storage_outputs.sh [environment] [--out-dir path] [--terraform-dir path]
#
# Example:
#   ./export_storage_outputs.sh dev --out-dir artifacts/storage/dev

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_ENVIRONMENT="dev"
ENVIRONMENT="$DEFAULT_ENVIRONMENT"

if [[ $# -gt 0 && "$1" != -* ]]; then
  ENVIRONMENT="$1"
  shift
fi

OUTPUT_DIR=""
TERRAFORM_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --terraform-dir)
      TERRAFORM_DIR="$2"
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
Usage: export_storage_outputs.sh [environment] [--out-dir path] [--terraform-dir path]

Options:
  --out-dir         Directory where JSON/.env artifacts will be stored.
                    Defaults to infra/artifacts/storage/<environment>/.
  --terraform-dir   Directory containing Terraform state for the environment.
                    Defaults to infra/terraform/environments/<environment>.
  -h, --help        Show this help message.
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 64
      ;;
  esac
done

if [[ -z "${TERRAFORM_DIR}" ]]; then
  TERRAFORM_DIR="${SCRIPT_DIR}/../terraform/environments/${ENVIRONMENT}"
fi

if [[ ! -d "${TERRAFORM_DIR}" ]]; then
  echo "Terraform directory '${TERRAFORM_DIR}' does not exist." >&2
  exit 1
fi

if [[ -z "${OUTPUT_DIR}" ]]; then
  OUTPUT_DIR="${SCRIPT_DIR}/../artifacts/storage/${ENVIRONMENT}"
fi

mkdir -p "${OUTPUT_DIR}"

if ! command -v terraform >/dev/null 2>&1; then
  echo "Terraform binary is not available on PATH." >&2
  exit 2
fi

pushd "${TERRAFORM_DIR}" >/dev/null

if [[ ! -f "terraform.tfstate" && ! -d "terraform.tfstate.d" ]]; then
  cat >&2 <<EOF
No Terraform state file detected in '${TERRAFORM_DIR}'.
Run 'terraform apply' for the environment before exporting outputs.
EOF
  popd >/dev/null
  exit 3
fi

OUTPUT_JSON_RAW="$(mktemp)"
trap 'rm -f "${OUTPUT_JSON_RAW}"' EXIT

terraform output -json > "${OUTPUT_JSON_RAW}"
popd >/dev/null

python3 <<'PYTHON' "${OUTPUT_JSON_RAW}" "${OUTPUT_DIR}/storage-outputs.json" "${OUTPUT_DIR}/storage-outputs.env"
import json
import sys
from pathlib import Path

raw_path, json_path, env_path = sys.argv[1:4]

with open(raw_path, "r", encoding="utf-8") as handle:
    data = json.load(handle)

keys = {
    "s3_bucket_conversation_logs": "CONVERSATION_LOGS_BUCKET_ARN",
    "s3_bucket_summaries": "SUMMARIES_BUCKET_ARN",
    "s3_bucket_media": "MEDIA_BUCKET_ARN",
    "ci_runner_role_arn": "CI_RUNNER_ROLE_ARN",
}

extracted = {}
missing = []
for terraform_key, env_key in keys.items():
    entry = data.get(terraform_key)
    if entry and isinstance(entry, dict):
        value = entry.get("value")
        if value:
            extracted[terraform_key] = value
            continue
    missing.append(terraform_key)

if missing:
    raise SystemExit(
        f"Missing Terraform outputs: {', '.join(missing)}. "
        "Run 'terraform apply' to refresh the state."
    )

json_path = Path(json_path)
env_path = Path(env_path)

json_path.write_text(json.dumps(extracted, indent=2), encoding="utf-8")

env_lines = []
for terraform_key, env_key in keys.items():
    value = extracted[terraform_key]
    env_lines.append(f"{env_key}={value}")

env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
PYTHON

echo "Storage outputs exported to:"
echo "  JSON: ${OUTPUT_DIR}/storage-outputs.json"
echo "  ENV : ${OUTPUT_DIR}/storage-outputs.env"
