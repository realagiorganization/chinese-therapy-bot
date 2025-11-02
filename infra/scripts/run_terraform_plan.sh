#!/usr/bin/env bash
# Convenience wrapper to generate a Terraform plan for the specified environment.
# Usage: ./run_terraform_plan.sh [environment] [additional terraform plan args...]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENVIRONMENT="${1:-dev}"
shift || true

TERRAFORM_DIR="${SCRIPT_DIR}/../terraform/environments/${ENVIRONMENT}"

if [[ ! -d "${TERRAFORM_DIR}" ]]; then
  echo "Environment directory '${TERRAFORM_DIR}' does not exist." >&2
  exit 1
fi

if ! command -v terraform >/dev/null 2>&1; then
  echo "Terraform is not installed or not on PATH." >&2
  exit 2
fi

determine_var_file() {
  if [[ -n "${TF_VARS_FILE:-}" ]]; then
    echo "${TF_VARS_FILE}"
    return
  fi

  local candidates=(
    "${TERRAFORM_DIR}/${ENVIRONMENT}.tfvars"
    "${TERRAFORM_DIR}/${ENVIRONMENT}.auto.tfvars"
    "${TERRAFORM_DIR}/../../${ENVIRONMENT}.tfvars"
    "${TERRAFORM_DIR}/../../${ENVIRONMENT}.auto.tfvars"
    "${TERRAFORM_DIR}/../../${ENVIRONMENT}.tfvars.example"
  )

  for candidate in "${candidates[@]}"; do
    if [[ -f "${candidate}" ]]; then
      echo "${candidate}"
      return
    fi
  done

  echo ""
}

VAR_FILE="$(determine_var_file)"

if [[ -z "${VAR_FILE}" ]]; then
  cat >&2 <<EOF
Unable to locate a tfvars file for environment '${ENVIRONMENT}'.
Set TF_VARS_FILE or place one of the following files:
  ${TERRAFORM_DIR}/${ENVIRONMENT}.tfvars
  ${TERRAFORM_DIR}/${ENVIRONMENT}.auto.tfvars
  ${TERRAFORM_DIR}/../../${ENVIRONMENT}.tfvars
  ${TERRAFORM_DIR}/../../${ENVIRONMENT}.auto.tfvars
EOF
  exit 3
fi

if [[ "${VAR_FILE}" == *".tfvars.example" ]]; then
  echo "⚠️  Using example variables file '${VAR_FILE}'. Replace with real credentials before applying." >&2
fi

pushd "${TERRAFORM_DIR}" >/dev/null

INIT_ARGS=("-upgrade")
if [[ -n "${TF_BACKEND_CONFIG_FILE:-}" ]]; then
  if [[ ! -f "${TF_BACKEND_CONFIG_FILE}" ]]; then
    echo "Backend config file '${TF_BACKEND_CONFIG_FILE}' not found." >&2
    exit 4
  fi
  INIT_ARGS+=("-backend-config=${TF_BACKEND_CONFIG_FILE}")
fi

terraform init "${INIT_ARGS[@]}"
terraform validate

PLAN_FILE="plan-${ENVIRONMENT}.tfplan"
PLAN_SUMMARY="plan-${ENVIRONMENT}.txt"

terraform plan \
  -var-file="${VAR_FILE}" \
  -out="${PLAN_FILE}" \
  "$@"

terraform show -no-color "${PLAN_FILE}" > "${PLAN_SUMMARY}"

popd >/dev/null

echo "Terraform plan written to ${TERRAFORM_DIR}/${PLAN_FILE}"
echo "Human-readable output written to ${TERRAFORM_DIR}/${PLAN_SUMMARY}"
