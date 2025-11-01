#!/usr/bin/env bash
# Fetch temporary AWS credentials for local development via STS assume-role.
# Usage: ./bootstrap-local-env.sh <role-arn> [session-name]

set -euo pipefail

ROLE_ARN="${1:-}"
SESSION_NAME="${2:-mindwell-local-dev}"

if [[ -z "${ROLE_ARN}" ]]; then
  echo "Usage: $0 <role-arn> [session-name]" >&2
  exit 1
fi

echo "Assuming role ${ROLE_ARN}..."
CREDS_JSON="$(aws sts assume-role \
  --role-arn "${ROLE_ARN}" \
  --role-session-name "${SESSION_NAME}" \
  --duration-seconds 3600)"

AWS_ACCESS_KEY_ID="$(jq -r '.Credentials.AccessKeyId' <<<"${CREDS_JSON}")"
AWS_SECRET_ACCESS_KEY="$(jq -r '.Credentials.SecretAccessKey' <<<"${CREDS_JSON}")"
AWS_SESSION_TOKEN="$(jq -r '.Credentials.SessionToken' <<<"${CREDS_JSON}")"
EXPIRATION="$(jq -r '.Credentials.Expiration' <<<"${CREDS_JSON}")"

cat > .env.local <<EOF
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN}
AWS_REGION=${AWS_REGION:-ap-northeast-1}
EOF

echo ".env.local updated. Credentials expire at ${EXPIRATION}."
