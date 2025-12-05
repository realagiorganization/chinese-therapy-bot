#!/usr/bin/env bash

set -euo pipefail

show_help() {
  cat <<'EOF'
Usage: check_infra_readiness.sh [options]

Runs terraform fmt/validate/test inside infra/terraform/environments/<env>
without touching remote state backends. Helpful when verifying Phase 2
artifacts before real cloud credentials are available.

Options:
  -e, --environment <name>  Target environment directory (default: dev).
      --skip-fmt            Skip terraform fmt -check.
      --skip-validate       Skip terraform init/validate.
      --skip-tests          Skip terraform test.
      --help                Show this message.
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "error: required command '$1' not found on PATH" >&2
    exit 1
  fi
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

ENVIRONMENT="dev"
RUN_FMT="true"
RUN_VALIDATE="true"
RUN_TESTS="true"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -e|--environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --skip-fmt)
      RUN_FMT="false"
      shift
      ;;
    --skip-validate)
      RUN_VALIDATE="false"
      shift
      ;;
    --skip-tests)
      RUN_TESTS="false"
      shift
      ;;
    --help|-h)
      show_help
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      show_help
      exit 1
      ;;
  esac
done

TF_DIR="${REPO_ROOT}/infra/terraform/environments/${ENVIRONMENT}"
if [[ ! -d "$TF_DIR" ]]; then
  echo "error: environment directory '${TF_DIR}' not found" >&2
  exit 1
fi

require_cmd terraform

pushd "$TF_DIR" >/dev/null

if [[ "$RUN_FMT" == "true" ]]; then
  echo ">> Running terraform fmt -check ..."
  terraform fmt -check -recursive .
fi

if [[ "$RUN_VALIDATE" == "true" ]]; then
  echo ">> Running terraform init (backend disabled) ..."
  terraform init -backend=false -input=false >/dev/null
  echo ">> Running terraform validate ..."
  terraform validate -no-color
fi

if [[ "$RUN_TESTS" == "true" ]]; then
  echo ">> Running terraform test ..."
  terraform test -no-color
fi

popd >/dev/null

echo "Infrastructure readiness checks completed."
