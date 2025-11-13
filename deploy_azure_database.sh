#!/usr/bin/env bash
# Provision Azure Database for PostgreSQL Flexible Server and emit the environment
# variables required by the backend deployment scripts.
set -euo pipefail

###########################################
# Defaults and global state
###########################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"

ENVIRONMENT="dev"
LOCATION="eastasia"
RESOURCE_GROUP=""
SUBSCRIPTION=""
NAME_PREFIX="mindwell"
NAME_SUFFIX=""

POSTGRES_SERVER_NAME=""
POSTGRES_VERSION="16"
POSTGRES_SKU="standard_d2ds_v5"
POSTGRES_TIER="GeneralPurpose"
POSTGRES_STORAGE_GB="64"
POSTGRES_HA_MODE="SameZone"
POSTGRES_BACKUP_RETENTION_DAYS="7"

ADMIN_USERNAME="mindwelladmin"
ADMIN_PASSWORD=""
DATABASE_NAME="mindwell"
FORCE_PASSWORD_ROTATION=0

ALLOW_AZURE_SERVICES=1
declare -a ALLOW_IPS=()

JSON_OUTPUT=0

###########################################
# Helpers
###########################################

usage() {
  cat <<'EOF'
Usage: ./deploy_azure_database.sh [options]

Creates (or reuses) an Azure Database for PostgreSQL Flexible Server instance and
prints the environment variables required by deploy_azure_hosting.sh.

Options:
  -e, --environment <name>          Deployment environment (default: dev).
  -l, --location <azure-region>     Azure region (default: eastasia).
  -g, --resource-group <name>       Resource group to use (default: rg-<prefix>-<env>).
  -s, --subscription <id|name>      Azure subscription (passes to az account set).
      --name-prefix <prefix>        Naming prefix (default: mindwell).
      --name-suffix <suffix>        Optional suffix appended to generated names.

PostgreSQL parameters:
      --postgres-server-name <name> Explicit server name (default: pgflex-<prefix>-<env>).
      --postgres-version <ver>      PostgreSQL major version (default: 16).
      --postgres-sku <sku>          Compute SKU (default: Standard_D2s_v5).
      --postgres-tier <tier>        Tier (Burstable, GeneralPurpose, MemoryOptimized).
      --postgres-storage <GiB>      Storage size in GiB (default: 64).
      --postgres-ha-mode <mode>     High availability mode (Disabled, SameZone, ZoneRedundant).
      --postgres-backup-days <n>    Backup retention in days (default: 7).

Credentials & database:
      --admin-username <name>       Administrator login (default: mindwelladmin).
      --admin-password <value>      Explicit admin password (otherwise randomly generated).
      --database-name <name>        Application database name (default: mindwell).
      --rotate-password             Force password rotation on existing server.

Networking:
      --allow-ip <IPv4>             Additional public IPv4 address to allow (can repeat).
      --no-allow-azure-services     Skip default 0.0.0.0 rule that allows Azure services.

Output:
      --json                        Emit machine-readable JSON summary instead of text.
  -h, --help                        Show this help message.

Example:
  ./deploy_azure_database.sh --environment staging --location southeastasia --allow-ip 203.0.113.12
EOF
}

log() {
  echo "[$(date '+%H:%M:%S')] $*" >&2
}

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

ensure_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "Command '$1' is required but not found in PATH."
  fi
}

ensure_provider_registered() {
  local namespace="$1"
  local state=""

  state="$(az provider show --namespace "$namespace" --query 'registrationState' -o tsv 2>/dev/null || true)"
  if [[ "$state" == "Registered" ]]; then
    return 0
  fi

  log "Registering Azure resource provider '$namespace'..."
  az provider register --namespace "$namespace" >/dev/null

  log "Waiting for provider '$namespace' registration to complete..."
  for attempt in {1..30}; do
    state="$(az provider show --namespace "$namespace" --query 'registrationState' -o tsv 2>/dev/null || true)"
    if [[ "$state" == "Registered" ]]; then
      return 0
    fi
    sleep 5
  done

  fail "Provider '$namespace' did not register successfully; current state: ${state:-unknown}."
}

normalize_name() {
  local raw="$1"
  local normalized
  normalized="$(echo "${raw,,}" | tr -c 'a-z0-9-' '-' | sed -E 's/-+/-/g; s/^-//; s/-$//')"
  [[ -z "$normalized" ]] && fail "Generated name from '$raw' is empty after normalization."
  if (( ${#normalized} < 3 || ${#normalized} > 63 )); then
    fail "Name '$normalized' must be between 3 and 63 characters after normalization."
  fi
  echo "$normalized"
}

generate_password() {
  python3 - <<'PY'
import secrets
import string

alphabet = string.ascii_letters + string.digits + "!@#%^*-_=+?"
password = "".join(secrets.choice(alphabet) for _ in range(24))
print(password)
PY
}

url_encode() {
  python3 - "$1" <<'PY'
import sys
from urllib.parse import quote_plus

print(quote_plus(sys.argv[1]))
PY
}

###########################################
# Argument parsing
###########################################

while [[ $# -gt 0 ]]; do
  case "$1" in
    -e|--environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    -l|--location)
      LOCATION="$2"
      shift 2
      ;;
    -g|--resource-group)
      RESOURCE_GROUP="$2"
      shift 2
      ;;
    -s|--subscription)
      SUBSCRIPTION="$2"
      shift 2
      ;;
    --name-prefix)
      NAME_PREFIX="$2"
      shift 2
      ;;
    --name-suffix)
      NAME_SUFFIX="$2"
      shift 2
      ;;
    --postgres-server-name)
      POSTGRES_SERVER_NAME="$2"
      shift 2
      ;;
    --postgres-version)
      POSTGRES_VERSION="$2"
      shift 2
      ;;
    --postgres-sku)
      POSTGRES_SKU="$2"
      shift 2
      ;;
    --postgres-tier)
      POSTGRES_TIER="$2"
      shift 2
      ;;
    --postgres-storage)
      POSTGRES_STORAGE_GB="$2"
      shift 2
      ;;
    --postgres-ha-mode)
      POSTGRES_HA_MODE="$2"
      shift 2
      ;;
    --postgres-backup-days)
      POSTGRES_BACKUP_RETENTION_DAYS="$2"
      shift 2
      ;;
    --admin-username)
      ADMIN_USERNAME="$2"
      shift 2
      ;;
    --admin-password)
      ADMIN_PASSWORD="$2"
      shift 2
      ;;
    --database-name)
      DATABASE_NAME="$2"
      shift 2
      ;;
    --rotate-password)
      FORCE_PASSWORD_ROTATION=1
      shift
      ;;
    --allow-ip)
      ALLOW_IPS+=("$2")
      shift 2
      ;;
    --no-allow-azure-services)
      ALLOW_AZURE_SERVICES=0
      shift
      ;;
    --json)
      JSON_OUTPUT=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown argument: $1"
      ;;
  esac
done

POSTGRES_SKU="${POSTGRES_SKU,,}"

###########################################
# Derived names & validation
###########################################

ensure_command az
ensure_command python3

BASE_NAME="${NAME_PREFIX}-${ENVIRONMENT}"
[[ -n "$NAME_SUFFIX" ]] && BASE_NAME="${BASE_NAME}-${NAME_SUFFIX}"

BASE_NAME="$(normalize_name "$BASE_NAME")"

if [[ -z "$RESOURCE_GROUP" ]]; then
  RESOURCE_GROUP="rg-${BASE_NAME}"
fi

if [[ -z "$POSTGRES_SERVER_NAME" ]]; then
  POSTGRES_SERVER_NAME="pgflex-${BASE_NAME}"
fi
POSTGRES_SERVER_NAME="$(normalize_name "$POSTGRES_SERVER_NAME")"

if [[ "$DATABASE_NAME" =~ [^a-zA-Z0-9_-] ]]; then
  fail "Database name '$DATABASE_NAME' contains invalid characters."
fi

if [[ -n "$SUBSCRIPTION" ]]; then
  log "Selecting Azure subscription '$SUBSCRIPTION'..."
  az account set --subscription "$SUBSCRIPTION" >/dev/null
fi

ensure_provider_registered "Microsoft.DBforPostgreSQL"

###########################################
# Resource provisioning
###########################################

if az group show --name "$RESOURCE_GROUP" >/dev/null 2>&1; then
  log "Resource group '$RESOURCE_GROUP' already exists."
else
  log "Creating resource group '$RESOURCE_GROUP' in '$LOCATION'..."
  az group create --name "$RESOURCE_GROUP" --location "$LOCATION" >/dev/null
fi

SERVER_EXISTS=0
if az postgres flexible-server show --resource-group "$RESOURCE_GROUP" --name "$POSTGRES_SERVER_NAME" >/dev/null 2>&1; then
  SERVER_EXISTS=1
  log "PostgreSQL server '$POSTGRES_SERVER_NAME' already exists."
fi

if [[ "$SERVER_EXISTS" -eq 1 && "$FORCE_PASSWORD_ROTATION" -eq 1 ]]; then
  if [[ -z "$ADMIN_PASSWORD" ]]; then
    ADMIN_PASSWORD="$(generate_password)"
  fi
  log "Rotating administrator password for '$POSTGRES_SERVER_NAME'..."
  az postgres flexible-server update \
    --resource-group "$RESOURCE_GROUP" \
    --name "$POSTGRES_SERVER_NAME" \
    --admin-password "$ADMIN_PASSWORD" >/dev/null
fi

if [[ "$SERVER_EXISTS" -eq 0 ]]; then
  if [[ -z "$ADMIN_PASSWORD" ]]; then
    ADMIN_PASSWORD="$(generate_password)"
    log "Generated administrator password for '$POSTGRES_SERVER_NAME'."
  fi

  log "Creating PostgreSQL Flexible Server '$POSTGRES_SERVER_NAME'..."
  az postgres flexible-server create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$POSTGRES_SERVER_NAME" \
    --location "$LOCATION" \
    --admin-user "$ADMIN_USERNAME" \
    --admin-password "$ADMIN_PASSWORD" \
    --version "$POSTGRES_VERSION" \
    --tier "$POSTGRES_TIER" \
    --sku-name "$POSTGRES_SKU" \
    --storage-size "$POSTGRES_STORAGE_GB" \
    --high-availability "$POSTGRES_HA_MODE" \
    --backup-retention "$POSTGRES_BACKUP_RETENTION_DAYS" \
    --public-access "0.0.0.0" >/dev/null
else
  if [[ -z "$ADMIN_PASSWORD" ]]; then
    fail "Existing server detected. Provide --admin-password (or --rotate-password) so the script can emit connection details."
  fi
fi

if az postgres flexible-server db show \
    --resource-group "$RESOURCE_GROUP" \
    --server-name "$POSTGRES_SERVER_NAME" \
    --database-name "$DATABASE_NAME" >/dev/null 2>&1; then
  log "Database '$DATABASE_NAME' already exists."
else
  log "Creating database '$DATABASE_NAME'..."
  az postgres flexible-server db create \
    --resource-group "$RESOURCE_GROUP" \
    --server-name "$POSTGRES_SERVER_NAME" \
    --database-name "$DATABASE_NAME" >/dev/null
fi

if [[ "$ALLOW_AZURE_SERVICES" -eq 1 ]]; then
  if ! az postgres flexible-server firewall-rule show \
      --resource-group "$RESOURCE_GROUP" \
      --name "$POSTGRES_SERVER_NAME" \
      --rule-name "allow-azure-services" >/dev/null 2>&1; then
    log "Creating firewall rule 'allow-azure-services' (0.0.0.0)."
    az postgres flexible-server firewall-rule create \
      --resource-group "$RESOURCE_GROUP" \
      --name "$POSTGRES_SERVER_NAME" \
      --rule-name "allow-azure-services" \
      --start-ip-address 0.0.0.0 \
      --end-ip-address 0.0.0.0 >/dev/null
  else
    log "Firewall rule 'allow-azure-services' already exists."
  fi
fi

rule_index=0
for ip in "${ALLOW_IPS[@]}"; do
  rule_name="allow-custom-${rule_index}"
  if az postgres flexible-server firewall-rule show \
      --resource-group "$RESOURCE_GROUP" \
      --name "$POSTGRES_SERVER_NAME" \
      --rule-name "$rule_name" >/dev/null 2>&1; then
    log "Firewall rule '$rule_name' already exists (IP $ip)."
  else
    log "Creating firewall rule '$rule_name' for $ip..."
    az postgres flexible-server firewall-rule create \
      --resource-group "$RESOURCE_GROUP" \
      --name "$POSTGRES_SERVER_NAME" \
      --rule-name "$rule_name" \
      --start-ip-address "$ip" \
      --end-ip-address "$ip" >/dev/null
  fi
  ((rule_index++))
done

###########################################
# Emit connection details
###########################################

SERVER_FQDN="$(az postgres flexible-server show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$POSTGRES_SERVER_NAME" \
  --query 'fullyQualifiedDomainName' -o tsv)"

[[ -z "$SERVER_FQDN" ]] && fail "Failed to resolve server FQDN."

ENCODED_USER="$(url_encode "$ADMIN_USERNAME")"
ENCODED_PASS="$(url_encode "$ADMIN_PASSWORD")"

DATABASE_URL="postgresql+asyncpg://${ENCODED_USER}:${ENCODED_PASS}@${SERVER_FQDN}:5432/${DATABASE_NAME}?sslmode=require"

if [[ "$JSON_OUTPUT" -eq 1 ]]; then
  python3 - <<PY
import json, sys

data = {
    "DATABASE_URL": "${DATABASE_URL}",
    "DB_HOST": "${SERVER_FQDN}",
    "DB_PORT": "5432",
    "DB_NAME": "${DATABASE_NAME}",
    "DB_USER": "${ADMIN_USERNAME}",
    "DB_PASSWORD": "${ADMIN_PASSWORD}",
    "RESOURCE_GROUP": "${RESOURCE_GROUP}",
    "POSTGRES_SERVER": "${POSTGRES_SERVER_NAME}"
}
json.dump(data, sys.stdout, indent=2)
PY
  echo
else
cat <<EOF
============================================================
Update these environment variables before running deploy_azure_hosting.sh
============================================================
DATABASE_URL=${DATABASE_URL}
DB_HOST=${SERVER_FQDN}
DB_PORT=5432
DB_NAME=${DATABASE_NAME}
DB_USER=${ADMIN_USERNAME}
DB_PASSWORD=${ADMIN_PASSWORD}
RESOURCE_GROUP=${RESOURCE_GROUP}
POSTGRES_SERVER=${POSTGRES_SERVER_NAME}
============================================================
EOF
fi

log "Done. Copy the values into your environment and rerun deploy_azure_hosting.sh."
