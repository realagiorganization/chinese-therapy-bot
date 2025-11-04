#!/usr/bin/env bash
# Validate that the local environment has the tooling and credentials required
# to run MindWell Terraform plans/applies for Azure AKS and AWS resources.

set -euo pipefail

missing=()

check_command() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    missing+=("${cmd}")
  fi
}

echo "🔍 Checking required command-line tools..."
for tool in terraform az aws; do
  check_command "${tool}"
done

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "❌ Missing required tools: ${missing[*]}" >&2
  echo "Install the tools above before running Terraform." >&2
  exit 2
fi
echo "✅ Terraform, Azure CLI, and AWS CLI detected."

echo
echo "🔍 Checking Azure authentication context..."

if [[ -n "${ARM_SUBSCRIPTION_ID:-}" ]]; then
  echo "✅ ARM_SUBSCRIPTION_ID is set (${ARM_SUBSCRIPTION_ID})."
else
  echo "⚠️  ARM_SUBSCRIPTION_ID is not set."
fi

if [[ -n "${ARM_TENANT_ID:-}" ]]; then
  echo "✅ ARM_TENANT_ID is set."
else
  echo "⚠️  ARM_TENANT_ID is not set."
fi

if [[ -n "${ARM_CLIENT_ID:-}" && -n "${ARM_CLIENT_SECRET:-}" ]]; then
  echo "✅ ARM_CLIENT_ID/ARM_CLIENT_SECRET detected (service principal auth)."
elif az account show >/dev/null 2>&1; then
  echo "✅ Azure CLI has an active login (az account show succeeded)."
else
  echo "❌ No Azure credentials detected. Run 'az login' or export ARM_* variables." >&2
  exit 3
fi

echo
echo "🔍 Checking AWS authentication context..."

# The AWS CLI exits non-zero when no default credentials are configured.
if aws sts get-caller-identity >/dev/null 2>&1; then
  echo "✅ AWS credentials detected via sts get-caller-identity."
else
  echo "❌ AWS credentials not available. Configure via 'aws configure', environment variables, or 'infra/scripts/assume_ci_role.sh'." >&2
  exit 4
fi

echo
echo "Check complete. Environment is ready for Terraform plan/apply runs."
