#!/usr/bin/env bash

set -euo pipefail

show_help() {
  cat <<'EOF'
Usage: provision_dev_infra.sh [options]

Runs Terraform for the specified environment, captures outputs, and optionally
fetches the AKS kubeconfig plus runs the workload identity validation job.

Options:
  -e, --environment <name>   Target environment directory (default: dev).
      --tfvars <path>        Optional tfvars file (relative to repo root).
      --backend-config <path>
                             Optional backend config file passed to terraform init.
      --plan-only            Generate the plan but skip apply.
      --skip-kubeconfig      Do not fetch kubeconfig even after apply.
      --validate-oidc        After apply + kubeconfig, run the workload identity
                             validation job defined in infra/kubernetes/samples.
      --help                 Show this help message.

Environment requirements:
  * terraform CLI available on PATH.
  * ARM_* variables or Azure CLI login configured for azurerm provider.
  * AWS credentials (env vars or profile) for S3/IAM resources.
  * az + kubectl binaries installed if kubeconfig/bootstrap steps are enabled.
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
TFVARS_FILE=""
BACKEND_CONFIG_FILE=""
PLAN_ONLY="false"
SKIP_KUBECONFIG="false"
VALIDATE_OIDC="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -e|--environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --tfvars)
      TFVARS_FILE="$2"
      shift 2
      ;;
    --backend-config)
      BACKEND_CONFIG_FILE="$2"
      shift 2
      ;;
    --plan-only)
      PLAN_ONLY="true"
      shift
      ;;
    --skip-kubeconfig)
      SKIP_KUBECONFIG="true"
      shift
      ;;
    --validate-oidc)
      VALIDATE_OIDC="true"
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

resolve_path() {
  local candidate="$1"
  if [[ -f "$candidate" ]]; then
    printf "%s" "$candidate"
    return 0
  fi
  if [[ -f "${REPO_ROOT}/${candidate}" ]]; then
    printf "%s" "${REPO_ROOT}/${candidate}"
    return 0
  fi
  return 1
}

TF_DIR="${REPO_ROOT}/infra/terraform/environments/${ENVIRONMENT}"
if [[ ! -d "$TF_DIR" ]]; then
  echo "error: environment directory '${TF_DIR}' not found" >&2
  exit 1
fi

TFVARS_PATH=""
if [[ -n "$TFVARS_FILE" ]]; then
  if ! TFVARS_PATH="$(resolve_path "$TFVARS_FILE")"; then
    echo "error: tfvars file '$TFVARS_FILE' not found (relative to repo root)" >&2
    exit 1
  fi
fi

BACKEND_CONFIG_PATH=""
if [[ -n "$BACKEND_CONFIG_FILE" ]]; then
  if ! BACKEND_CONFIG_PATH="$(resolve_path "$BACKEND_CONFIG_FILE")"; then
    echo "error: backend config file '$BACKEND_CONFIG_FILE' not found" >&2
    exit 1
  fi
fi

require_cmd terraform
if [[ "$PLAN_ONLY" != "true" && "$SKIP_KUBECONFIG" != "true" ]]; then
  if command -v az >/dev/null 2>&1; then
    :
  else
    echo "warning: az CLI not found; kubeconfig bootstrap will be skipped" >&2
    SKIP_KUBECONFIG="true"
  fi
fi
if [[ "$VALIDATE_OIDC" == "true" ]]; then
  require_cmd kubectl
fi
require_cmd jq

OUTPUT_DIR="${REPO_ROOT}/artifacts/provisioning/${ENVIRONMENT}"
mkdir -p "$OUTPUT_DIR"

timestamp="$(date +%Y%m%d%H%M%S)"
plan_path="${OUTPUT_DIR}/${ENVIRONMENT}-${timestamp}.tfplan"
outputs_path="${OUTPUT_DIR}/${ENVIRONMENT}-terraform-outputs.json"
kubeconfig_path="${OUTPUT_DIR}/kubeconfig-${ENVIRONMENT}.yaml"
oidc_log_path="${OUTPUT_DIR}/oidc-validation-${timestamp}.log"

pushd "$TF_DIR" >/dev/null

init_cmd=(terraform init -input=false)
if [[ -n "$BACKEND_CONFIG_PATH" ]]; then
  init_cmd+=("-backend-config=${BACKEND_CONFIG_PATH}")
fi
"${init_cmd[@]}"

plan_cmd=(terraform plan -input=false -out "$plan_path")
if [[ -n "$TFVARS_PATH" ]]; then
  plan_cmd+=("-var-file=${TFVARS_PATH}")
fi
"${plan_cmd[@]}"

if [[ "$PLAN_ONLY" == "true" ]]; then
  echo "Terraform plan stored at ${plan_path}"
  popd >/dev/null
  exit 0
fi

terraform apply -input=false "$plan_path"
terraform output -json > "$outputs_path"
echo "Terraform outputs written to ${outputs_path}"

resource_group="$(jq -r '.resource_group_name.value // empty' "$outputs_path")"
aks_name="$(jq -r '.aks_cluster_name.value // empty' "$outputs_path")"

if [[ -n "$resource_group" && -n "$aks_name" && "$SKIP_KUBECONFIG" != "true" ]]; then
  echo "Fetching kubeconfig for ${aks_name} (${resource_group})"
  az aks get-credentials \
    --resource-group "$resource_group" \
    --name "$aks_name" \
    --file "$kubeconfig_path" \
    --overwrite-existing
  echo "Kubeconfig saved to ${kubeconfig_path}"
else
  echo "Skipping kubeconfig fetch (missing az CLI, resource outputs, or flag disabled)."
fi

if [[ "$VALIDATE_OIDC" == "true" && -f "$kubeconfig_path" ]]; then
  sample_manifest="${REPO_ROOT}/infra/kubernetes/samples/workload-identity-validation.yaml"
  if [[ ! -f "$sample_manifest" ]]; then
    echo "warning: workload identity manifest not found at ${sample_manifest}, skipping validation."
  else
    echo "Running workload identity validation job..."
    KUBECONFIG="$kubeconfig_path" kubectl apply -f "$sample_manifest"
    set +e
    KUBECONFIG="$kubeconfig_path" kubectl wait \
      --for=condition=complete job/mindwell-workload-identity \
      --timeout=180s
    wait_status=$?
    set -e
    KUBECONFIG="$kubeconfig_path" kubectl logs job/mindwell-workload-identity > "$oidc_log_path" || true
    KUBECONFIG="$kubeconfig_path" kubectl delete -f "$sample_manifest" --ignore-not-found >/dev/null 2>&1 || true
    if [[ $wait_status -ne 0 ]]; then
      echo "warning: workload identity job did not complete successfully (see ${oidc_log_path})."
    else
      echo "OIDC validation completed. Logs saved to ${oidc_log_path}."
    fi
  fi
fi

popd >/dev/null

echo "Provisioning workflow complete."
