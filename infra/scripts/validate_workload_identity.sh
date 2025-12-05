#!/usr/bin/env bash
# Applies the workload identity validation manifest after templating secrets and IDs.
# Captures the job logs and optionally cleans up the namespace once finished.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DEFAULT_MANIFEST="${REPO_ROOT}/infra/kubernetes/samples/workload-identity-validation.yaml"
DEFAULT_OUTPUT_DIR="${REPO_ROOT}/artifacts/oidc-validation"

TENANT_ID=""
CLIENT_ID=""
KEY_VAULT_NAME=""
SECRET_NAME="postgres-admin-password"
NAMESPACE="workload-identity-validation"
JOB_NAME="keyvault-secret-validation"
OUTPUT_DIR="${DEFAULT_OUTPUT_DIR}"
MANIFEST_PATH="${DEFAULT_MANIFEST}"
KEEP_RESOURCES="false"
KUBECONFIG_PATH="${KUBECONFIG:-}"
TERRAFORM_OUTPUTS=""
TIMEOUT_SECONDS=180
ENVIRONMENT_LABEL="dev"

show_help() {
  cat <<'EOF'
Usage: validate_workload_identity.sh [options]

Options:
  --tenant-id <id>              Azure tenant ID used by workload identity.
  --client-id <id>              Managed identity (kubelet/workload) client ID.
  --key-vault <name>            Azure Key Vault name that hosts the secret.
  --secret-name <name>          Secret to fetch (default: postgres-admin-password).
  --namespace <name>            Namespace used by the validation manifest.
  --job-name <name>             Job name inside the manifest.
  --manifest <path>             Source manifest template to render.
  --kubeconfig <path>           Explicit kubeconfig path (defaults to \$KUBECONFIG).
  --terraform-outputs <path>    terraform output -json file to auto-populate values.
  --output-dir <path>           Directory to store validation logs/artifacts.
  --environment <label>         Label appended to log filenames (default: dev).
  --timeout <seconds>           Wait timeout for the job (default: 180).
  --keep-resources              Do not delete the namespace/job after completion.
  --help                        Show this message.

Either pass the tenant/client/vault values explicitly or supply
--terraform-outputs pointing at the JSON produced by terraform output -json.
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "error: required command '$1' not found on PATH" >&2
    exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tenant-id)
      TENANT_ID="$2"
      shift 2
      ;;
    --client-id)
      CLIENT_ID="$2"
      shift 2
      ;;
    --key-vault)
      KEY_VAULT_NAME="$2"
      shift 2
      ;;
    --secret-name)
      SECRET_NAME="$2"
      shift 2
      ;;
    --namespace)
      NAMESPACE="$2"
      shift 2
      ;;
    --job-name)
      JOB_NAME="$2"
      shift 2
      ;;
    --manifest)
      MANIFEST_PATH="$2"
      shift 2
      ;;
    --kubeconfig)
      KUBECONFIG_PATH="$2"
      shift 2
      ;;
    --terraform-outputs)
      TERRAFORM_OUTPUTS="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --environment)
      ENVIRONMENT_LABEL="$2"
      shift 2
      ;;
    --timeout)
      TIMEOUT_SECONDS="$2"
      shift 2
      ;;
    --keep-resources)
      KEEP_RESOURCES="true"
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

require_cmd kubectl
require_cmd jq
require_cmd python3

if [[ -n "$TERRAFORM_OUTPUTS" ]]; then
  if [[ ! -f "$TERRAFORM_OUTPUTS" ]]; then
    echo "error: terraform outputs file '$TERRAFORM_OUTPUTS' not found" >&2
    exit 1
  fi
  if [[ -z "$CLIENT_ID" ]]; then
    CLIENT_ID="$(jq -r '.kubelet_identity_client_id.value // empty' "$TERRAFORM_OUTPUTS")"
  fi
  if [[ -z "$KEY_VAULT_NAME" ]]; then
    KEY_VAULT_NAME="$(jq -r '.key_vault_name.value // empty' "$TERRAFORM_OUTPUTS")"
  fi
  if [[ -z "$TENANT_ID" ]]; then
    TENANT_ID="$(jq -r '.azure_tenant_id.value // empty' "$TERRAFORM_OUTPUTS")"
  fi
fi

if [[ -z "$CLIENT_ID" || -z "$TENANT_ID" || -z "$KEY_VAULT_NAME" ]]; then
  echo "error: tenant ID, client ID, and key vault name are required." >&2
  echo "Provide them via CLI flags or --terraform-outputs." >&2
  exit 1
fi

if [[ ! -f "$MANIFEST_PATH" ]]; then
  echo "error: manifest template '$MANIFEST_PATH' not found" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

if [[ -n "$KUBECONFIG_PATH" ]]; then
  export KUBECONFIG="$KUBECONFIG_PATH"
fi

timestamp="$(date +%Y%m%d%H%M%S)"
log_path="${OUTPUT_DIR}/${ENVIRONMENT_LABEL}-oidc-${timestamp}.log"
rendered_manifest="$(mktemp)"

cleanup() {
  rm -f "$rendered_manifest"
}
trap cleanup EXIT

python3 - <<'PY' "$MANIFEST_PATH" "$rendered_manifest" "$CLIENT_ID" "$TENANT_ID" "$KEY_VAULT_NAME" "$SECRET_NAME"
import sys
from pathlib import Path

template_path, output_path, client_id, tenant_id, key_vault_name, secret_name = sys.argv[1:]
text = Path(template_path).read_text(encoding="utf-8")
replacements = {
    "<WORKLOAD_IDENTITY_CLIENT_ID>": client_id,
    "<AZURE_TENANT_ID>": tenant_id,
    "<KEY_VAULT_NAME>": key_vault_name,
    "<SECRET_NAME>": secret_name,
}
for placeholder, value in replacements.items():
    text = text.replace(placeholder, value)
Path(output_path).write_text(text, encoding="utf-8")
PY

echo "Applying workload identity validation resources in namespace '${NAMESPACE}'..."
kubectl apply -f "$rendered_manifest" >/dev/null

set +e
kubectl wait \
  --namespace "$NAMESPACE" \
  --for=condition=complete \
  "job/${JOB_NAME}" \
  --timeout="${TIMEOUT_SECONDS}s"
wait_status=$?
set -e

kubectl logs -n "$NAMESPACE" "job/${JOB_NAME}" > "$log_path" 2>&1 || true

if [[ "$KEEP_RESOURCES" != "true" ]]; then
  kubectl delete -f "$rendered_manifest" --ignore-not-found >/dev/null 2>&1 || true
fi

if [[ $wait_status -ne 0 ]]; then
  echo "warning: workload identity job did not complete within ${TIMEOUT_SECONDS}s." >&2
  echo "Review logs at ${log_path} for troubleshooting."
  exit 1
fi

echo "OIDC validation job completed successfully."
echo "Logs stored at ${log_path} (contains Key Vault secret output; handle carefully)."
