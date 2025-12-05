#!/usr/bin/env bash
# Tear down Azure resources created by deploy_azure_database.sh and deploy_azure_hosting.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"

ENVIRONMENT="dev"
RESOURCE_GROUP=""
SUBSCRIPTION=""
NAME_PREFIX="mindwell"
NAME_SUFFIX=""

POSTGRES_SERVER_NAME=""
FRONTEND_APP_NAME=""
BACKEND_PLAN_NAME=""
BACKEND_APP_NAME=""
OAUTH_PLAN_NAME=""
OAUTH_APP_NAME=""

DELETE_RESOURCE_GROUP=0
ASSUME_YES=0

usage() {
  cat <<'EOF'
Usage: ./destroy_azure_resources.sh [options]

Deletes the Azure resources provisioned by deploy_azure_database.sh and
deploy_azure_hosting.sh. Resource names are derived the same way as the
deployment scripts, but you can override them explicitly.

Options:
  -e, --environment <name>           Environment suffix (default: dev).
  -g, --resource-group <name>        Resource group (default: rg-<prefix>-<env>).
  -s, --subscription <id|name>       Azure subscription to use.
      --name-prefix <prefix>         Naming prefix (default: mindwell).
      --name-suffix <suffix>         Optional suffix appended to generated names.

  --postgres-server-name <name>      PostgreSQL Flexible Server name (default: pgflex-<prefix>-<env>).
  --frontend-app-name <name>         Static Web App name (default: <prefix>-<env>-web[<suffix>]).
  --backend-plan-name <name>         Backend App Service plan name (default: asp-<prefix>-<env>-api[<suffix>]).
  --backend-app-name <name>          Backend WebApp name (default: <prefix>-<env>-api[<suffix>]).
  --oauth-plan-name <name>           oauth2-proxy App Service plan name (default: asp-<prefix>-<env>-oauth[<suffix>]).
  --oauth-app-name <name>            oauth2-proxy WebApp name (default: <prefix>-<env>-oauth[<suffix>]).

  --delete-resource-group            Delete the resource group after removing resources.
  -y, --yes                          Do not prompt for confirmation.
  -h, --help                         Show this help message.

Example:
  ./destroy_azure_resources.sh --environment staging --name-suffix blue --delete-resource-group
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

while [[ $# -gt 0 ]]; do
  case "$1" in
    -e|--environment)
      ENVIRONMENT="$2"
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
    --frontend-app-name)
      FRONTEND_APP_NAME="$2"
      shift 2
      ;;
    --backend-plan-name)
      BACKEND_PLAN_NAME="$2"
      shift 2
      ;;
    --backend-app-name)
      BACKEND_APP_NAME="$2"
      shift 2
      ;;
    --oauth-plan-name)
      OAUTH_PLAN_NAME="$2"
      shift 2
      ;;
    --oauth-app-name)
      OAUTH_APP_NAME="$2"
      shift 2
      ;;
    --delete-resource-group)
      DELETE_RESOURCE_GROUP=1
      shift
      ;;
    -y|--yes)
      ASSUME_YES=1
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

if [[ -z "$RESOURCE_GROUP" ]]; then
  RESOURCE_GROUP="rg-${NAME_PREFIX}-${ENVIRONMENT}"
fi

if [[ -z "$POSTGRES_SERVER_NAME" ]]; then
  POSTGRES_SERVER_NAME="pgflex-${NAME_PREFIX}-${ENVIRONMENT}"
fi

if [[ -z "$FRONTEND_APP_NAME" ]]; then
  FRONTEND_APP_NAME="${NAME_PREFIX}-${ENVIRONMENT}-web"
fi
if [[ -z "$BACKEND_PLAN_NAME" ]]; then
  BACKEND_PLAN_NAME="asp-${NAME_PREFIX}-${ENVIRONMENT}-api"
fi
if [[ -z "$BACKEND_APP_NAME" ]]; then
  BACKEND_APP_NAME="${NAME_PREFIX}-${ENVIRONMENT}-api"
fi
if [[ -z "$OAUTH_PLAN_NAME" ]]; then
  OAUTH_PLAN_NAME="asp-${NAME_PREFIX}-${ENVIRONMENT}-oauth"
fi
if [[ -z "$OAUTH_APP_NAME" ]]; then
  OAUTH_APP_NAME="${NAME_PREFIX}-${ENVIRONMENT}-oauth"
fi

if [[ -n "$NAME_SUFFIX" ]]; then
  RESOURCE_GROUP="${RESOURCE_GROUP}-${NAME_SUFFIX}"
  POSTGRES_SERVER_NAME="${POSTGRES_SERVER_NAME}-${NAME_SUFFIX}"
  FRONTEND_APP_NAME="${FRONTEND_APP_NAME}-${NAME_SUFFIX}"
  BACKEND_PLAN_NAME="${BACKEND_PLAN_NAME}-${NAME_SUFFIX}"
  BACKEND_APP_NAME="${BACKEND_APP_NAME}-${NAME_SUFFIX}"
  OAUTH_PLAN_NAME="${OAUTH_PLAN_NAME}-${NAME_SUFFIX}"
  OAUTH_APP_NAME="${OAUTH_APP_NAME}-${NAME_SUFFIX}"
fi

RESOURCE_GROUP="$(normalize_name "$RESOURCE_GROUP")"
POSTGRES_SERVER_NAME="$(normalize_name "$POSTGRES_SERVER_NAME")"
FRONTEND_APP_NAME="$(normalize_name "$FRONTEND_APP_NAME")"
BACKEND_PLAN_NAME="$(normalize_name "$BACKEND_PLAN_NAME")"
BACKEND_APP_NAME="$(normalize_name "$BACKEND_APP_NAME")"
OAUTH_PLAN_NAME="$(normalize_name "$OAUTH_PLAN_NAME")"
OAUTH_APP_NAME="$(normalize_name "$OAUTH_APP_NAME")"

ensure_command az

if [[ -n "$SUBSCRIPTION" ]]; then
  az account set --subscription "$SUBSCRIPTION" >/dev/null
fi

if ! az account show >/dev/null 2>&1; then
  fail "Azure CLI is not logged in. Run 'az login' first."
fi

log "Target resource group: $RESOURCE_GROUP"
log "Planned deletions:"
log "  - PostgreSQL Flexible Server: $POSTGRES_SERVER_NAME"
log "  - Backend WebApp: $BACKEND_APP_NAME"
log "  - Backend App Service plan: $BACKEND_PLAN_NAME"
log "  - oauth2-proxy WebApp: $OAUTH_APP_NAME"
log "  - oauth2-proxy App Service plan: $OAUTH_PLAN_NAME"
log "  - Static Web App: $FRONTEND_APP_NAME"
if [[ "$DELETE_RESOURCE_GROUP" -eq 1 ]]; then
  log "  - Resource group (after above): $RESOURCE_GROUP"
fi

if [[ "$ASSUME_YES" -ne 1 ]]; then
  read -r -p "Proceed with deleting the resources listed above? [y/N]: " answer
  case "$answer" in
    y|Y)
      ;;
    *)
      log "Aborted by user."
      exit 1
      ;;
  esac
fi

log "Deleting Static Web App '$FRONTEND_APP_NAME' (if present)..."
if az staticwebapp show --name "$FRONTEND_APP_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
  az staticwebapp delete --name "$FRONTEND_APP_NAME" --resource-group "$RESOURCE_GROUP" --yes >/dev/null
else
  log "Static Web App '$FRONTEND_APP_NAME' not found; skipping."
fi

log "Deleting backend WebApp '$BACKEND_APP_NAME' (if present)..."
if az webapp show --name "$BACKEND_APP_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
  az webapp delete --name "$BACKEND_APP_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null
else
  log "Backend WebApp '$BACKEND_APP_NAME' not found; skipping."
fi

log "Deleting oauth2-proxy WebApp '$OAUTH_APP_NAME' (if present)..."
if az webapp show --name "$OAUTH_APP_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
  az webapp delete --name "$OAUTH_APP_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null
else
  log "oauth2-proxy WebApp '$OAUTH_APP_NAME' not found; skipping."
fi

log "Deleting backend App Service plan '$BACKEND_PLAN_NAME' (if present)..."
if az appservice plan show --name "$BACKEND_PLAN_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
  az appservice plan delete --name "$BACKEND_PLAN_NAME" --resource-group "$RESOURCE_GROUP" --yes >/dev/null
else
  log "Backend App Service plan '$BACKEND_PLAN_NAME' not found; skipping."
fi

if [[ "$OAUTH_PLAN_NAME" != "$BACKEND_PLAN_NAME" ]]; then
  log "Deleting oauth2-proxy App Service plan '$OAUTH_PLAN_NAME' (if present)..."
  if az appservice plan show --name "$OAUTH_PLAN_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
    az appservice plan delete --name "$OAUTH_PLAN_NAME" --resource-group "$RESOURCE_GROUP" --yes >/dev/null
  else
    log "oauth2-proxy App Service plan '$OAUTH_PLAN_NAME' not found; skipping."
  fi
fi

log "Deleting PostgreSQL Flexible Server '$POSTGRES_SERVER_NAME' (if present)..."
if az postgres flexible-server show --resource-group "$RESOURCE_GROUP" --name "$POSTGRES_SERVER_NAME" >/dev/null 2>&1; then
  az postgres flexible-server delete --resource-group "$RESOURCE_GROUP" --name "$POSTGRES_SERVER_NAME" --yes >/dev/null
else
  log "PostgreSQL server '$POSTGRES_SERVER_NAME' not found; skipping."
fi

if [[ "$DELETE_RESOURCE_GROUP" -eq 1 ]]; then
  log "Deleting resource group '$RESOURCE_GROUP'..."
  if az group show --name "$RESOURCE_GROUP" >/dev/null 2>&1; then
    az group delete --name "$RESOURCE_GROUP" --yes >/dev/null
  else
    log "Resource group '$RESOURCE_GROUP' not found; skipping deletion."
  fi
fi

log "Teardown completed."
