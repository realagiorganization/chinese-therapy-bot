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
      --skip-credential-checks
                             Do not verify Azure/AWS credentials before running Terraform.
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
SKIP_CREDENTIAL_CHECKS="false"

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
    --skip-credential-checks)
      SKIP_CREDENTIAL_CHECKS="true"
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

has_azure_cli_login() {
  if ! command -v az >/dev/null 2>&1; then
    return 1
  fi
  if az account show >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

check_azure_credentials() {
  if [[ -n "${ARM_USE_MSI:-}" && "${ARM_USE_MSI}" != "false" ]]; then
    if [[ -z "${ARM_SUBSCRIPTION_ID:-}" || -z "${ARM_TENANT_ID:-}" ]]; then
      echo "error: ARM_USE_MSI is enabled but ARM_SUBSCRIPTION_ID or ARM_TENANT_ID is unset." >&2
      return 1
    fi
    return 0
  fi

  if [[ -n "${ARM_CLIENT_ID:-}" && -n "${ARM_CLIENT_SECRET:-}" && -n "${ARM_TENANT_ID:-}" && -n "${ARM_SUBSCRIPTION_ID:-}" ]]; then
    return 0
  fi

  if [[ -n "${ARM_OIDC_TOKEN_FILE_PATH:-}" && -n "${ARM_CLIENT_ID:-}" && -n "${ARM_TENANT_ID:-}" && -n "${ARM_SUBSCRIPTION_ID:-}" ]]; then
    return 0
  fi

  if has_azure_cli_login; then
    return 0
  fi

  cat >&2 <<'EOF'
error: Azure credentials not detected.
Provide ARM_* environment variables for a service principal, enable ARM_USE_MSI,
or log in via the Azure CLI (az login). Use --skip-credential-checks to bypass
this guard if you are supplying credentials through an alternate mechanism.
EOF
  return 1
}

check_aws_credentials() {
  if [[ -n "${AWS_ACCESS_KEY_ID:-}" && -n "${AWS_SECRET_ACCESS_KEY:-}" ]]; then
    return 0
  fi

  if [[ -n "${AWS_PROFILE:-}" ]]; then
    return 0
  fi

  if [[ -n "${AWS_WEB_IDENTITY_TOKEN_FILE:-}" && -n "${AWS_ROLE_ARN:-}" ]]; then
    return 0
  fi

  cat >&2 <<'EOF'
error: AWS credentials not detected.
Export AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY, configure AWS_PROFILE, or set up
web identity variables (AWS_WEB_IDENTITY_TOKEN_FILE + AWS_ROLE_ARN).
Use --skip-credential-checks to bypass this guard if another credential source
is available to Terraform.
EOF
  return 1
}

if [[ "$SKIP_CREDENTIAL_CHECKS" != "true" ]]; then
  check_azure_credentials
  check_aws_credentials
fi

OUTPUT_DIR="${REPO_ROOT}/artifacts/provisioning/${ENVIRONMENT}"
mkdir -p "$OUTPUT_DIR"

timestamp="$(date +%Y%m%d%H%M%S)"
plan_path="${OUTPUT_DIR}/${ENVIRONMENT}-${timestamp}.tfplan"
outputs_path="${OUTPUT_DIR}/${ENVIRONMENT}-terraform-outputs.json"
kubeconfig_path="${OUTPUT_DIR}/kubeconfig-${ENVIRONMENT}.yaml"

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
  validation_script="${SCRIPT_DIR}/validate_workload_identity.sh"
  if [[ ! -x "$validation_script" ]]; then
    echo "warning: validation script not found at ${validation_script}, skipping validation."
  else
    echo "Running workload identity validation job..."
    secret_target="${OIDC_SECRET_NAME:-postgres-admin-password}"
    timeout_seconds="${OIDC_VALIDATION_TIMEOUT:-180}"
    if ! "$validation_script" \
      --kubeconfig "$kubeconfig_path" \
      --terraform-outputs "$outputs_path" \
      --output-dir "$OUTPUT_DIR" \
      --secret-name "$secret_target" \
      --environment "$ENVIRONMENT" \
      --timeout "$timeout_seconds"
    then
      echo "warning: workload identity job did not complete successfully. Check logs under ${OUTPUT_DIR}." >&2
    fi
  fi
fi

popd >/dev/null

echo "Provisioning workflow complete."
