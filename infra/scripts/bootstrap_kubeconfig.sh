#!/usr/bin/env bash
# Fetches AKS kubeconfig credentials for CI runners or local operators.
# Usage: ./bootstrap_kubeconfig.sh [environment] [resource-group] [cluster-name]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENVIRONMENT="${1:-dev}"
ARG_RESOURCE_GROUP="${2:-}"
ARG_CLUSTER_NAME="${3:-}"

TERRAFORM_DIR="${SCRIPT_DIR}/../terraform/environments/${ENVIRONMENT}"

if [[ ! -d "${TERRAFORM_DIR}" ]]; then
  echo "Environment directory '${TERRAFORM_DIR}' does not exist." >&2
  exit 1
fi

if ! command -v az >/dev/null 2>&1; then
  echo "Azure CLI (az) is required but not installed." >&2
  exit 2
fi

pushd "${TERRAFORM_DIR}" >/dev/null

resolve_output() {
  local name="$1"
  terraform output -raw "${name}" 2>/dev/null || true
}

RESOURCE_GROUP="${ARG_RESOURCE_GROUP:-$(resolve_output "resource_group_name")}"
CLUSTER_NAME="${ARG_CLUSTER_NAME:-$(resolve_output "aks_cluster_name")}"

popd >/dev/null

if [[ -z "${RESOURCE_GROUP}" || -z "${CLUSTER_NAME}" ]]; then
  cat >&2 <<EOF
Unable to determine AKS resource group or cluster name.
Either provide them explicitly:
  ./bootstrap_kubeconfig.sh ${ENVIRONMENT} <resource-group> <cluster-name>
or ensure 'terraform output' can resolve 'resource_group_name' and 'aks_cluster_name'.
EOF
  exit 3
fi

echo "Retrieving kubeconfig for AKS cluster '${CLUSTER_NAME}' in resource group '${RESOURCE_GROUP}'..."

az aks get-credentials \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CLUSTER_NAME}" \
  --overwrite-existing

echo "Kubeconfig merged into \$HOME/.kube/config."
