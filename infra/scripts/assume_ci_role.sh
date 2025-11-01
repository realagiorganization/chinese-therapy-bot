#!/usr/bin/env bash
# Assume an AWS role for the CI Runner Agent using GitHub OIDC.

set -euo pipefail

ROLE_ARN="${1:-}"
SESSION_NAME="${2:-mindwell-ci-runner}"
DURATION="${3:-3600}"

if [[ -z "${ROLE_ARN}" ]]; then
  echo "Usage: $0 <role-arn> [session-name] [duration-seconds]" >&2
  exit 1
fi

if [[ -z "${ACTIONS_ID_TOKEN_REQUEST_URL:-}" || -z "${ACTIONS_ID_TOKEN_REQUEST_TOKEN:-}" ]]; then
  echo "GitHub OIDC environment variables are missing. This script must run inside GitHub Actions." >&2
  exit 2
fi

OIDC_TOKEN="$(curl -sSL \
  -H "Authorization: Bearer ${ACTIONS_ID_TOKEN_REQUEST_TOKEN}" \
  "${ACTIONS_ID_TOKEN_REQUEST_URL}&audience=sts.amazonaws.com" \
  | jq -r '.value')"

if [[ -z "${OIDC_TOKEN}" || "${OIDC_TOKEN}" == "null" ]]; then
  echo "Failed to obtain OIDC token from GitHub." >&2
  exit 3
fi

CREDS_JSON="$(aws sts assume-role-with-web-identity \
  --role-arn "${ROLE_ARN}" \
  --role-session-name "${SESSION_NAME}" \
  --duration-seconds "${DURATION}" \
  --web-identity-token "${OIDC_TOKEN}")"

AWS_ACCESS_KEY_ID="$(jq -r '.Credentials.AccessKeyId' <<<"${CREDS_JSON}")"
AWS_SECRET_ACCESS_KEY="$(jq -r '.Credentials.SecretAccessKey' <<<"${CREDS_JSON}")"
AWS_SESSION_TOKEN="$(jq -r '.Credentials.SessionToken' <<<"${CREDS_JSON}")"
EXPIRATION="$(jq -r '.Credentials.Expiration' <<<"${CREDS_JSON}")"

{
  echo "AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}"
  echo "AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}"
  echo "AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN}"
  echo "AWS_CREDENTIAL_EXPIRATION=${EXPIRATION}"
} >> "${GITHUB_ENV:-/tmp/mindwell-ci-env}"

echo "AWS credentials exported to GitHub environment; expires at ${EXPIRATION}."
