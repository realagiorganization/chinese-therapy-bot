#!/usr/bin/env bash
# Deploy MindWell services to Azure Static Web Apps (frontend) and Azure App Service (backend + oauth2-proxy).
set -euo pipefail

###########################################
# Defaults and argument parsing
###########################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"

ENVIRONMENT="dev"
LOCATION="eastasia"
RESOURCE_GROUP=""
SUBSCRIPTION=""
NAME_PREFIX="mindwell"
NAME_SUFFIX=""

FRONTEND_APP_NAME=""
FRONTEND_API_URL=""
FRONTEND_SWA_SKU="Free"
SWA_DEPLOY_PACKAGE="${SWA_DEPLOY_PACKAGE:-@azure/static-web-apps-cli@1.1.7}"
SWA_DEPLOY_ENVIRONMENT="${SWA_DEPLOY_ENVIRONMENT:-production}"

BACKEND_APP_NAME=""
BACKEND_PLAN_NAME=""
BACKEND_PLAN_SKU="B1"
BACKEND_PYTHON_VERSION="PYTHON|3.11"
BACKEND_RUN_FROM_PACKAGE=0
BACKEND_FORCE_DOCKER_PIP="${BACKEND_FORCE_DOCKER_PIP:-0}"
BACKEND_PIP_ONLY_BINARY="${BACKEND_PIP_ONLY_BINARY:-pydantic-core}"
AZURE_TARGET_GLIBC="${AZURE_TARGET_GLIBC:-2.31}"
BACKEND_STARTUP_COMMAND='bash -lc "APP_DIR=\"\${APP_PATH:-/home/site/wwwroot}\"; cd \"\$APP_DIR\"; exec ./azure_startup.sh"'
BACKEND_RUN_FROM_PACKAGE_EFFECTIVE=0
SKIP_KUDU_CLEANUP="${SKIP_KUDU_CLEANUP:-0}"
KUDU_PROFILE_CACHE=""

OAUTH_APP_NAME=""
OAUTH_PLAN_NAME=""
OAUTH_PLAN_SKU="B1"
OAUTH_IMAGE_DEFAULT="mindwelloauthacr.azurecr.io/oauth2-proxy:v7.8.1-cors"
OAUTH_IMAGE="${OAUTH_IMAGE:-$OAUTH_IMAGE_DEFAULT}"
OAUTH_CONTAINER_PORT="4180"
OAUTH_ENV_FILE="${HOME}/.config/mindwell/oauth2-proxy.azure.env"

BACKEND_ENV_LIST_VAR="BACKEND_APP_SETTINGS"

DIST_DIR_RELATIVE="clients/web/dist"
FRONTEND_SOURCE_RELATIVE="clients/web"
BACKEND_SOURCE_RELATIVE="services/backend"
BACKEND_CONFIG_RELATIVE="services/backend/app/core/config.py"

usage() {
  cat <<'EOF'
Usage: ./deploy_azure_hosting.sh [options]

Required Azure prerequisites:
  - Azure CLI (az) logged in (az login) and subscription set or provided via --subscription.
  - Sufficient permissions to create resource groups, Static Web Apps, and App Services.
  - Все необходимые переменные окружения (кроме oauth2-proxy) должны быть экспортированы в окружение
    (например, через ~/.bashrc). Скрипт автоматически собирает список ключей из
    services/backend/app/core/config.py. Дополнительно можно указать переменную
    BACKEND_APP_SETTINGS для явного добавления ключей.

Options:
  -e, --environment <name>         Environment suffix used in generated resource names. Default: dev.
  -l, --location <azure-region>    Azure region for all resources. Default: eastasia.
  -g, --resource-group <name>      Existing or new resource group. Default: rg-<prefix>-<env>.
  -s, --subscription <id|name>     Azure subscription to use.
      --name-prefix <prefix>       Prefix for all generated resource names. Default: mindwell.
      --name-suffix <suffix>       Optional suffix appended to resource names.

Frontend:
      --frontend-app-name <name>   Static Web App name. Default: <prefix>-<env>-web[<suffix>].
      --frontend-api-url <url>     API base URL injected as VITE_API_BASE_URL. Defaults to backend host.
      --frontend-sku <sku>         Static Web App SKU (Free, Standard, Dedicated). Default: Free.

Backend:
      --backend-app-name <name>    Azure WebApp (backend) name. Default: <prefix>-<env>-api[<suffix>].
      --backend-plan-name <name>   App Service plan for backend. Default: asp-<prefix>-<env>-api[<suffix>].
      --backend-plan-sku <sku>     App Service plan SKU. Default: B1.
      --backend-python <stack>     Azure runtime stack (e.g. PYTHON|3.11). Default: PYTHON|3.11.
      --backend-run-from-package   Принудительно включает WEBSITE_RUN_FROM_PACKAGE=1 и собирает
                                   зависимости локально. По умолчанию скрипт автоматически
                                   переключится на этот режим, если Oryx build завершится с
                                   ошибкой. Зависимости упаковываются с использованием локального
                                   Python или Docker-образа mcr.microsoft.com/oryx/python:<версия>.
      --backend-startup-command    Custom startup command passed to App Service. По умолчанию
                                   используется `bash -lc "<команда без set -euo>"`, которая просто
                                   переходит в ${APP_PATH:-/home/site/wwwroot} и запускает
                                   azure_startup.sh (готовит PYTHONPATH и стартует gunicorn).
                                   Всё содержимое хранится в одной строке, чтобы Oryx корректно
                                   передал startup-команду.

oauth2-proxy:
      --oauth-app-name <name>      Azure WebApp (oauth2-proxy) name. Default: <prefix>-<env>-oauth[<suffix>].
      --oauth-plan-name <name>     App Service plan for oauth2-proxy. Default: asp-<prefix>-<env>-oauth[<suffix>].
      --oauth-plan-sku <sku>       Plan SKU. Default: B1.
      --oauth-image <image>        Container image for oauth2-proxy. Default: mindwelloauthacr.azurecr.io/oauth2-proxy:v7.8.1-cors
                                   (соберите/запушьте образ из infra/docker/oauth2-proxy перед запуском).
      --oauth-port <port>          Container listen port (sets WEBSITES_PORT). Default: 4180.

General:
  -h, --help                       Show this help.

The script will:
  1. Build the frontend via npm (clients/web).
  2. Create/update Azure Static Web App and upload the build.
  3. Package the backend (services/backend) and deploy via zip to Azure App Service.
  4. Provision an oauth2-proxy App Service backed by the specified container image.
  5. Print the resulting hostnames for all services.

Environment conventions:
  - Переменные для backend извлекаются из services/backend/app/core/config.py. Значения
    берутся из текущего окружения (включая ~/.bashrc). BACKEND_APP_SETTINGS можно
    использовать для добавления дополнительных ключей (через пробел или запятую).
  - BACKEND_FORCE_DOCKER_PIP=1 заставит упаковку зависимостей выполняться внутри
    контейнера mcr.microsoft.com/oryx/python:<версия>, что помогает избежать
    несовместимости glibc между WSL/desktop и Azure App Service.
  - BACKEND_PIP_ONLY_BINARY задаёт значение PIP_ONLY_BINARY на время pip install
    (по умолчанию pydantic-core). Можно указать ':all:' или конкретные пакеты,
    чтобы принудить установку wheel вместо сборки из исходников.
  - AZURE_TARGET_GLIBC задаёт минимальную версию glibc целевой среды
    (по умолчанию 2.31). Если локальная glibc выше, зависимости автоматически
    собираются внутри Docker-контейнера, чтобы избежать несовместимых wheel.
  - Параметры oauth2-proxy читаются из файла ~/.config/mindwell/oauth2-proxy.azure.env.
EOF
}

###########################################
# Helper functions
###########################################

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
  echo "$normalized"
}

detect_glibc_version() {
  if ! command -v ldd >/dev/null 2>&1; then
    return 1
  fi
  local first_line
  if ! first_line="$(ldd --version 2>/dev/null | head -n 1)"; then
    return 1
  fi
  local version
  version="$(printf '%s\n' "$first_line" | grep -Eo '[0-9]+(\.[0-9]+)+' | tail -n 1)"
  [[ -n "$version" ]] || return 1
  printf '%s' "$version"
}

version_gt() {
  local lhs="$1"
  local rhs="$2"
  [[ -z "$lhs" || -z "$rhs" ]] && return 1
  local IFS=.
  read -ra left_parts <<<"$lhs"
  read -ra right_parts <<<"$rhs"
  local len="${#left_parts[@]}"
  if [[ "${#right_parts[@]}" -gt "$len" ]]; then
    len="${#right_parts[@]}"
  fi
  local i
  for ((i = 0; i < len; i++)); do
    local a="${left_parts[i]:-0}"
    local b="${right_parts[i]:-0}"
    if ((10#$a > 10#$b)); then
      return 0
    elif ((10#$a < 10#$b)); then
      return 1
    fi
  done
  return 1
}

read_settings_file() {
  local file_path="$1"
  local -n target_array="$2"
  target_array=()

  [[ ! -f "$file_path" ]] && fail "Settings file '$file_path' does not exist."

  while IFS= read -r line || [[ -n "$line" ]]; do
    # Skip blank lines and comments
    [[ -z "$line" ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    target_array+=("$line")
  done < "$file_path"
}

parse_key_list() {
  local raw="$1"
  local -n target="$2"
  target=()
  [[ -z "$raw" ]] && return 0
  while IFS= read -r token; do
    token="${token#"${token%%[![:space:]]*}"}"
    token="${token%"${token##*[![:space:]]}"}"
    [[ -z "$token" ]] && continue
    target+=("$token")
  done < <(printf '%s' "$raw" | tr ', ' '\n')
}

collect_backend_env_keys() {
  local config_path="$1"

  [[ -f "$config_path" ]] || fail "Backend config file '$config_path' not found."

  python3 - "$config_path" <<'PY'
import ast
import sys
from pathlib import Path

config_path = Path(sys.argv[1])

try:
    source = config_path.read_text(encoding="utf-8")
except FileNotFoundError:
    sys.stderr.write(f"Missing backend config file: {config_path}\n")
    sys.exit(1)

tree = ast.parse(source, filename=str(config_path))
aliases = set()


class BackendSettingsVisitor(ast.NodeVisitor):
    def visit_ClassDef(self, node):
        if node.name != "AppSettings":
            return
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign):
                alias = self._extract_alias(stmt)
                if alias:
                    aliases.add(alias)

    @staticmethod
    def _extract_alias(node):
        target = node.target
        if not isinstance(target, ast.Name):
            return None
        field_name = target.id
        call = node.value
        alias_value = None
        if isinstance(call, ast.Call):
            for kw in call.keywords:
                if kw.arg == "alias":
                    try:
                        alias_value = ast.literal_eval(kw.value)
                    except Exception:
                        alias_value = None
                    break
        if not alias_value:
            alias_value = field_name.upper()
        if isinstance(alias_value, str):
            return alias_value
        return None


BackendSettingsVisitor().visit(tree)

for alias in sorted(aliases):
    print(alias)
PY
}

get_kudu_credentials() {
  local profile
  if [[ -z "$KUDU_PROFILE_CACHE" ]]; then
    KUDU_PROFILE_CACHE="$(az webapp deployment list-publishing-profiles \
      --name "$BACKEND_APP_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --query "[?publishMethod=='MSDeploy']|[0].{user:userName,password:userPWD}" \
      -o tsv 2>/dev/null || true)"
  fi
  profile="$KUDU_PROFILE_CACHE"
  [[ -z "$profile" ]] && return 1
  printf '%s' "$profile"
}

run_kudu_command() {
  local command="$1"
  local profile kudu_user kudu_pass payload response

  if ! profile="$(get_kudu_credentials)"; then
    return 1
  fi
  IFS=$'\t' read -r kudu_user kudu_pass <<<"$profile"
  [[ -z "$kudu_user" || -z "$kudu_pass" ]] && return 1

  payload="$(python3 - "$command" <<'PY'
import json
import sys

print(json.dumps({"command": sys.argv[1]}))
PY
)" || return 1

  response="$(curl -sS --fail \
    -u "$kudu_user:$kudu_pass" \
    -H "Content-Type: application/json" \
    -d "$payload" \
    "https://${BACKEND_APP_NAME}.scm.azurewebsites.net/api/command" 2>/dev/null)" || return 1

  [[ "$response" == *'"ExitCode":0'* ]]
}

kudu_api_get() {
  local endpoint="$1"
  local profile kudu_user kudu_pass

  if ! profile="$(get_kudu_credentials)"; then
    return 1
  fi

  IFS=$'\t' read -r kudu_user kudu_pass <<<"$profile"
  [[ -z "$kudu_user" || -z "$kudu_pass" ]] && return 1

  curl -sS --fail \
    -u "$kudu_user:$kudu_pass" \
    "https://${BACKEND_APP_NAME}.scm.azurewebsites.net${endpoint}" \
    2>/dev/null
}

kudu_deployment_succeeded_since() {
  local since_epoch="$1"
  local payload
  [[ -z "$since_epoch" ]] && return 1

  if ! payload="$(kudu_api_get "/api/deployments/latest")"; then
    return 1
  fi

  if KUDU_DEPLOYMENT_JSON="$payload" python3 - "$since_epoch" <<'PY'; then
import json
import os
import sys
from datetime import datetime, timezone

since_epoch = float(sys.argv[1])
payload = os.environ.get("KUDU_DEPLOYMENT_JSON", "")
if not payload:
    raise SystemExit(1)

data = json.loads(payload)
status_text = str(data.get("status_text") or data.get("statusText") or "").lower()
status_code = str(data.get("status") or "").lower()
if status_text != "success" and status_code not in {"4", "success"}:
    raise SystemExit(1)

def parse_timestamp(value):
    if not value:
        return None
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    t_pos = value.find("T")
    tz_sep = -1
    for idx in range(len(value) - 1, t_pos, -1):
        if value[idx] in "+-":
            tz_sep = idx
            break
    if tz_sep == -1:
        base = value
        tz = "+00:00"
    else:
        base = value[:tz_sep]
        tz = value[tz_sep:]
    if "." in base:
        main, frac = base.split(".", 1)
        frac_digits = "".join(ch for ch in frac if ch.isdigit())
        frac_digits = (frac_digits + "000000")[:6]
        base = f"{main}.{frac_digits}" if frac_digits else main
    ts = base + tz
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None

end_time = parse_timestamp(
    data.get("end_time")
    or data.get("endTime")
    or data.get("last_success_end_time")
    or data.get("lastSuccessEndTime")
)
received_time = parse_timestamp(data.get("received_time") or data.get("receivedTime"))

if received_time and received_time.timestamp() + 5 < since_epoch:
    raise SystemExit(1)

if end_time and end_time.timestamp() >= since_epoch:
    raise SystemExit(0)

raise SystemExit(1)
PY
    return 0
  fi
  return 1
}

kudu_deployment_failed_since() {
  local since_epoch="$1"
  local payload
  [[ -z "$since_epoch" ]] && return 1

  if ! payload="$(kudu_api_get "/api/deployments/latest")"; then
    return 1
  fi

  if KUDU_DEPLOYMENT_JSON="$payload" python3 - "$since_epoch" <<'PY'; then
import json
import os
import sys
from datetime import datetime

since_epoch = float(sys.argv[1])
payload = os.environ.get("KUDU_DEPLOYMENT_JSON", "")
if not payload:
    raise SystemExit(1)

data = json.loads(payload)
status_text = str(data.get("status_text") or data.get("statusText") or "").lower()
status_code = str(data.get("status") or "").lower()
failed = status_text in {"failed", "fail", "error"} or status_code in {"3", "failed", "error"}
if not failed:
    raise SystemExit(1)

def parse_timestamp(value):
    if not value:
        return None
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    t_pos = value.find("T")
    tz_sep = -1
    for idx in range(len(value) - 1, t_pos, -1):
        if value[idx] in "+-":
            tz_sep = idx
            break
    if tz_sep == -1:
        base = value
        tz = "+00:00"
    else:
        base = value[:tz_sep]
        tz = value[tz_sep:]
    if "." in base:
        main, frac = base.split(".", 1)
        frac_digits = "".join(ch for ch in frac if ch.isdigit())
        frac_digits = (frac_digits + "000000")[:6]
        base = f"{main}.{frac_digits}" if frac_digits else main
    ts = base + tz
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None

end_time = parse_timestamp(
    data.get("end_time")
    or data.get("endTime")
    or data.get("complete_time")
    or data.get("completeTime")
)
received_time = parse_timestamp(data.get("received_time") or data.get("receivedTime"))

if received_time and received_time.timestamp() + 5 < since_epoch:
    raise SystemExit(1)

if end_time and end_time.timestamp() >= since_epoch:
    raise SystemExit(0)

raise SystemExit(1)
PY
    return 0
  fi
  return 1
}

wait_for_kudu_deployment() {
  local since_epoch="$1"
  local timeout="${2:-600}"
  local interval="${3:-10}"
  local start_time deadline now

  [[ -z "$since_epoch" ]] && return 2

  start_time="$(date +%s)"
  deadline=$((start_time + timeout))

  while :; do
    now="$(date +%s)"
    if (( now > deadline )); then
      log "Kudu OneDeploy не завершился за ${timeout}s ожидания."
      return 2
    fi
    if kudu_deployment_succeeded_since "$since_epoch"; then
      log "Kudu OneDeploy завершился успешно через $((now - start_time))s."
      return 0
    fi
    if kudu_deployment_failed_since "$since_epoch"; then
      log "Kudu OneDeploy сообщил об ошибке через $((now - start_time))s."
      return 1
    fi
    sleep "$interval"
  done
}

cleanup_remote_python_artifacts() {
  local cleanup_cmd="rm -rf /home/site/wwwroot/.python_packages /home/site/wwwroot/antenv /home/site/wwwroot/output.tar.gz /home/site/wwwroot/oryx-manifest.toml /home/site/wwwroot/oryx-manifest.json"
  run_kudu_command "$cleanup_cmd"
}

is_local_connection_host() {
  local host="${1,,}"
  case "$host" in
    ""|"localhost"|localhost.*|*.localdomain|*.local)
      return 0
      ;;
  esac
  if [[ "$host" == "[::1]" || "$host" == "::1" ]]; then
    return 0
  fi
  if [[ "$host" == "0.0.0.0" ]]; then
    return 0
  fi
  if [[ "$host" == 127.* ]]; then
    return 0
  fi
  return 1
}

should_skip_backend_env_setting() {
  local key="$1"
  local value="$2"

  if [[ "$key" == "DATABASE_URL" && -n "$value" ]]; then
    if [[ "$value" =~ @([^/?#]+) ]]; then
      local host_port="${BASH_REMATCH[1]}"
      local host="${host_port%%:*}"
      if ! is_local_connection_host "$host"; then
        return 1
      fi
      log "Skipping DATABASE_URL that points to local host '$host'. Azure контейнер не сможет подключиться к вашей локальной БД; задайте внешний адрес через BACKEND_APP_SETTINGS или az webapp config appsettings set."
      return 0
    fi
  fi

  return 1
}

install_backend_dependencies() {
  local stage_dir="$1"
  local requirements_file="$2"
  local requested_version="$3"

  local site_packages_dir="$stage_dir/.python_packages/lib/site-packages"
  local used_docker=0
  rm -rf "$stage_dir/.python_packages"
  mkdir -p "$site_packages_dir"

  local pip_log="$stage_dir/.pip_install.log"
  rm -f "$pip_log"
  local pip_only_binary="$BACKEND_PIP_ONLY_BINARY"
  if [[ -n "$pip_only_binary" ]]; then
    log "PIP_ONLY_BINARY='$pip_only_binary' будет применён при установке backend зависимостей."
  fi
  local pip_only_binary_args=()
  if [[ -n "$pip_only_binary" ]]; then
    pip_only_binary_args=( "--only-binary" "$pip_only_binary" )
  fi

  local local_python_version=""
  local_python_version="$(python3 - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}", end="")
PY
)"

  local requirements_basename
  requirements_basename="$(basename "$requirements_file")"

  local use_docker=0
  local docker_reason=""
  if [[ -n "$requested_version" && "$requested_version" != "$local_python_version" ]]; then
    use_docker=1
    docker_reason="локальный Python ${local_python_version:-unknown} не совпадает с $requested_version"
  elif [[ "$BACKEND_FORCE_DOCKER_PIP" -eq 1 ]]; then
    use_docker=1
    docker_reason="BACKEND_FORCE_DOCKER_PIP=1"
  fi

  if [[ -n "${AZURE_TARGET_GLIBC:-}" ]]; then
    local detected_glibc=""
    if detected_glibc="$(detect_glibc_version)"; then
      if version_gt "$detected_glibc" "$AZURE_TARGET_GLIBC"; then
        use_docker=1
        if [[ -n "$docker_reason" ]]; then
          docker_reason+=", "
        fi
        docker_reason+="локальная glibc $detected_glibc > целевой $AZURE_TARGET_GLIBC"
      fi
    fi
  fi

  if [[ "$use_docker" -eq 1 ]]; then
    if command -v docker >/dev/null 2>&1; then
      log "Устанавливаем зависимости внутри контейнера Docker (${docker_reason})."
      if docker run --rm \
        --user "$(id -u):$(id -g)" \
        -v "${stage_dir}:/workspace" \
        -w /workspace \
        -e REQ_FILE="$requirements_basename" \
        -e PY_VERSION="$requested_version" \
        -e PIP_ONLY_BINARY="$pip_only_binary" \
        "mcr.microsoft.com/oryx/python:${requested_version}" \
        bash -lc 'set -euo pipefail
pip_args=()
if [[ -n "${PIP_ONLY_BINARY:-}" ]]; then
  pip_args+=("--only-binary" "${PIP_ONLY_BINARY}")
fi
PYTHON_BIN="python3"
if [[ -n "${PY_VERSION:-}" && -x "/opt/python/${PY_VERSION}/bin/python3" ]]; then
  PYTHON_BIN="/opt/python/${PY_VERSION}/bin/python3"
elif [[ -x "/opt/python/3/bin/python3" ]]; then
  PYTHON_BIN="/opt/python/3/bin/python3"
fi
if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
  "$PYTHON_BIN" -m ensurepip --upgrade >/dev/null 2>&1 || "$PYTHON_BIN" -m ensurepip >/dev/null 2>&1
fi
"$PYTHON_BIN" -m pip install --disable-pip-version-check --no-cache-dir "${pip_args[@]}" --target .python_packages/lib/site-packages -r "$REQ_FILE"' \
        >"$pip_log" 2>&1; then
        used_docker=1
        if ! chmod -R u+rwX "$stage_dir/.python_packages" >/dev/null 2>&1; then
          log "Warning: chmod не смог обновить права в .python_packages после docker install (продолжаем, т.к. файлы принадлежат $(id -un))."
        fi
      else
        log "Установка зависимостей в Docker завершилась с ошибкой. Последние строки журнала:"
        tail -n 50 "$pip_log" || true
        cp "$pip_log" "$REPO_ROOT/backend_pip_install_failed.log" >/dev/null 2>&1 || true
        fail "pip install внутри Docker завершился неуспешно (лог сохранён в backend_pip_install_failed.log)."
      fi
    else
      local reason="${docker_reason:-Python $requested_version несовместим с локальной средой}"
      fail "Run-From-Package требует Docker для сборки зависимостей (${reason}). Установите Docker или запустите скрипт в среде с совместимой glibc."
    fi
  else
    log "Installing backend dependencies locally (python $local_python_version)..."
    if PIP_ONLY_BINARY="$pip_only_binary" python3 -m pip install \
      --disable-pip-version-check \
      --no-cache-dir \
      "${pip_only_binary_args[@]}" \
      --target "$site_packages_dir" \
      -r "$requirements_file" \
      >"$pip_log" 2>&1; then
      :
    else
      log "pip install на локальной машине завершился с ошибкой. Последние строки журнала:"
      tail -n 50 "$pip_log" || true
      cp "$pip_log" "$REPO_ROOT/backend_pip_install_failed.log" >/dev/null 2>&1 || true
      fail "pip install локально завершился неуспешно (лог сохранён в backend_pip_install_failed.log)."
    fi
  fi

  rm -f "$pip_log"

  local enforce_crypto_spec="cryptography>=41,<42"
  log "Ensuring $enforce_crypto_spec installed inside packaged site-packages..."
  if [[ "$used_docker" -eq 1 ]]; then
    if docker run --rm \
      --user "$(id -u):$(id -g)" \
      -v "${stage_dir}:/workspace" \
      -w /workspace \
      -e PY_VERSION="$requested_version" \
      -e ENFORCE_SPEC="$enforce_crypto_spec" \
      -e PIP_ONLY_BINARY="$pip_only_binary" \
      "mcr.microsoft.com/oryx/python:${requested_version}" \
      bash -lc 'set -euo pipefail
pip_args=()
if [[ -n "${PIP_ONLY_BINARY:-}" ]]; then
  pip_args+=("--only-binary" "${PIP_ONLY_BINARY}")
fi
PYTHON_BIN="python3"
if [[ -n "${PY_VERSION:-}" && -x "/opt/python/${PY_VERSION}/bin/python3" ]]; then
  PYTHON_BIN="/opt/python/${PY_VERSION}/bin/python3"
elif [[ -x "/opt/python/3/bin/python3" ]]; then
  PYTHON_BIN="/opt/python/3/bin/python3"
fi
if ! "$PYTHON_BIN" -m pip install --disable-pip-version-check --no-cache-dir --no-deps --upgrade \
  "${pip_args[@]}" \
  --target .python_packages/lib/site-packages "${ENFORCE_SPEC:?}"; then
  echo "Failed to enforce ${ENFORCE_SPEC} inside docker" >&2
  exit 1
fi' >/dev/null; then
      :
    else
      fail "Не удалось зафиксировать версию cryptography (docker)."
    fi
  else
    if ! PIP_ONLY_BINARY="$pip_only_binary" python3 -m pip install \
      --disable-pip-version-check \
      --no-cache-dir \
      --no-deps \
      --upgrade \
      "${pip_only_binary_args[@]}" \
      --target "$site_packages_dir" \
      "$enforce_crypto_spec" >/dev/null 2>&1; then
      fail "Не удалось зафиксировать версию cryptography (local pip)."
    fi
  fi

  local validation_script="$stage_dir/.validate_imports.py"
  cat >"$validation_script" <<'PY'
import importlib
import sys

modules = ("uvicorn", "pydantic_core")

for module in modules:
    try:
        importlib.import_module(module)
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(f"Не удалось импортировать модуль {module} внутри упакованного окружения: {exc}\n")
        raise
PY

  log "Validating uvicorn/pydantic_core availability inside staged site-packages..."

  local validation_ok=0
  if [[ "$used_docker" -eq 1 ]]; then
    if docker run --rm \
      --user "$(id -u):$(id -g)" \
      -v "${stage_dir}:/workspace" \
      -w /workspace \
      -e PY_VERSION="$requested_version" \
      "mcr.microsoft.com/oryx/python:${requested_version}" \
      bash -lc 'set -euo pipefail
PYTHON_BIN="python3"
if [[ -n "${PY_VERSION:-}" && -x "/opt/python/${PY_VERSION}/bin/python3" ]]; then
  PYTHON_BIN="/opt/python/${PY_VERSION}/bin/python3"
elif [[ -x "/opt/python/3/bin/python3" ]]; then
  PYTHON_BIN="/opt/python/3/bin/python3"
fi
PYTHONPATH="/workspace:/workspace/.python_packages/lib/site-packages" "$PYTHON_BIN" /workspace/.validate_imports.py' >/dev/null; then
      validation_ok=1
    fi
  else
    if PYTHONPATH="${stage_dir}:${site_packages_dir}" python3 "$validation_script" >/dev/null; then
      validation_ok=1
    fi
  fi

  rm -f "$validation_script"

  if [[ "$validation_ok" -ne 1 ]]; then
    fail "Не удалось проверить установленные модули внутри упакованного окружения."
  fi
}

prepare_run_from_package_tarball() {
  local stage_dir="$1"
  local tar_path="$stage_dir/output.tar.gz"
  local stage_parent
  stage_parent="$(dirname "$stage_dir")"
  local tmp_tar
  tmp_tar="$(mktemp "${stage_parent}/output.tar.gz.XXXXXX")"
  log "Упаковываем stage в output.tar.gz для Azure Run-From-Package..."
  if tar -czf "$tmp_tar" --exclude='./output.tar.gz' -C "$stage_dir" . >/dev/null; then
    mv "$tmp_tar" "$tar_path"
    if [[ -f "$tar_path" ]]; then
      log "output.tar.gz готов ($(du -h "$tar_path" | awk '{print $1}'))."
    else
      fail "Не удалось создать $tar_path."
    fi
  else
    rm -f "$tmp_tar"
    fail "tar не смог собрать $tar_path."
  fi
}

###########################################
# Load shell environment
###########################################

if [[ -f "${HOME}/.bashrc" ]]; then
  set +u
  # shellcheck disable=SC1090
  source "${HOME}/.bashrc"
  set -u
else
  log "Warning: ~/.bashrc not found; proceeding with existing environment."
fi

###########################################
# Argument parsing
###########################################

while [[ $# -gt 0 ]]; do
  case "$1" in
    -e|--environment) ENVIRONMENT="$2"; shift 2 ;;
    -l|--location) LOCATION="$2"; shift 2 ;;
    -g|--resource-group) RESOURCE_GROUP="$2"; shift 2 ;;
    -s|--subscription) SUBSCRIPTION="$2"; shift 2 ;;
    --name-prefix) NAME_PREFIX="$2"; shift 2 ;;
    --name-suffix) NAME_SUFFIX="$2"; shift 2 ;;

    --frontend-app-name) FRONTEND_APP_NAME="$2"; shift 2 ;;
    --frontend-api-url) FRONTEND_API_URL="$2"; shift 2 ;;
    --frontend-sku) FRONTEND_SWA_SKU="$2"; shift 2 ;;

    --backend-app-name) BACKEND_APP_NAME="$2"; shift 2 ;;
    --backend-plan-name) BACKEND_PLAN_NAME="$2"; shift 2 ;;
    --backend-plan-sku) BACKEND_PLAN_SKU="$2"; shift 2 ;;
    --backend-python) BACKEND_PYTHON_VERSION="$2"; shift 2 ;;
    --backend-run-from-package) BACKEND_RUN_FROM_PACKAGE=1; shift ;;
    --backend-startup-command) BACKEND_STARTUP_COMMAND="$2"; shift 2 ;;

    --oauth-app-name) OAUTH_APP_NAME="$2"; shift 2 ;;
    --oauth-plan-name) OAUTH_PLAN_NAME="$2"; shift 2 ;;
    --oauth-plan-sku) OAUTH_PLAN_SKU="$2"; shift 2 ;;
    --oauth-image) OAUTH_IMAGE="$2"; shift 2 ;;
    --oauth-port) OAUTH_CONTAINER_PORT="$2"; shift 2 ;;

    -h|--help) usage; exit 0 ;;
    *) fail "Unknown argument: $1" ;;
  esac
done

###########################################
# Derived configuration
###########################################

if [[ -z "$RESOURCE_GROUP" ]]; then
  RESOURCE_GROUP="rg-${NAME_PREFIX}-${ENVIRONMENT}"
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
  FRONTEND_APP_NAME="${FRONTEND_APP_NAME}-${NAME_SUFFIX}"
  BACKEND_PLAN_NAME="${BACKEND_PLAN_NAME}-${NAME_SUFFIX}"
  BACKEND_APP_NAME="${BACKEND_APP_NAME}-${NAME_SUFFIX}"
  OAUTH_PLAN_NAME="${OAUTH_PLAN_NAME}-${NAME_SUFFIX}"
  OAUTH_APP_NAME="${OAUTH_APP_NAME}-${NAME_SUFFIX}"
fi

RESOURCE_GROUP="$(normalize_name "$RESOURCE_GROUP")"
FRONTEND_APP_NAME="$(normalize_name "$FRONTEND_APP_NAME")"
BACKEND_PLAN_NAME="$(normalize_name "$BACKEND_PLAN_NAME")"
BACKEND_APP_NAME="$(normalize_name "$BACKEND_APP_NAME")"
OAUTH_PLAN_NAME="$(normalize_name "$OAUTH_PLAN_NAME")"
OAUTH_APP_NAME="$(normalize_name "$OAUTH_APP_NAME")"

FRONTEND_DIR="$REPO_ROOT/$FRONTEND_SOURCE_RELATIVE"
DIST_DIR="$REPO_ROOT/$DIST_DIR_RELATIVE"
BACKEND_DIR="$REPO_ROOT/$BACKEND_SOURCE_RELATIVE"
BACKEND_CONFIG_FILE="$REPO_ROOT/$BACKEND_CONFIG_RELATIVE"

[[ ! -d "$FRONTEND_DIR" ]] && fail "Frontend directory '$FRONTEND_DIR' not found."
[[ ! -f "$FRONTEND_DIR/package.json" ]] && fail "package.json not found in '$FRONTEND_DIR'."
[[ ! -d "$BACKEND_DIR" ]] && fail "Backend directory '$BACKEND_DIR' not found."
[[ ! -f "$BACKEND_DIR/pyproject.toml" ]] && fail "pyproject.toml not found in '$BACKEND_DIR'."
[[ ! -f "$BACKEND_CONFIG_FILE" ]] && fail "Backend config file '$BACKEND_CONFIG_FILE' not found."

###########################################
# Pre-flight checks
###########################################

ensure_command az
ensure_command npm
ensure_command npx
ensure_command python3
ensure_command zip
ensure_command curl
ensure_command rsync

[[ -f "$OAUTH_ENV_FILE" ]] || fail "oauth2-proxy env file '$OAUTH_ENV_FILE' not found. Создайте его согласно инструкциям."

if [[ -n "$SUBSCRIPTION" ]]; then
  az account set --subscription "$SUBSCRIPTION" >/dev/null
fi

if ! az account show >/dev/null 2>&1; then
  fail "Azure CLI is not logged in. Run 'az login' first."
fi

###########################################
# Working directories
###########################################

AZ_COMMAND_PATH="$(command -v az || true)"
AZ_USES_WINDOWS=0
if [[ -n "$AZ_COMMAND_PATH" && "$AZ_COMMAND_PATH" == /mnt/* ]]; then
  AZ_USES_WINDOWS=1
  WINDOWS_TMP_ROOT="/mnt/c/tmp"
  mkdir -p "$WINDOWS_TMP_ROOT"
  WORK_ROOT="$(mktemp -d -p "$WINDOWS_TMP_ROOT" mindwell_deploy_XXXXXX)"
else
  WORK_ROOT="$(mktemp -d)"
fi

cleanup() {
  rm -rf "$WORK_ROOT"
}
trap cleanup EXIT

convert_path_for_az() {
  local path="$1"
  if [[ "$AZ_USES_WINDOWS" -eq 1 && -n "$path" ]]; then
    if command -v wslpath >/dev/null 2>&1; then
      wslpath -w "$path"
      return
    fi
  fi
  echo "$path"
}

###########################################
# Step 1: Ensure resource group
###########################################

log "Ensuring resource group '$RESOURCE_GROUP' in '$LOCATION'..."
if ! az group show --name "$RESOURCE_GROUP" >/dev/null 2>&1; then
  az group create --name "$RESOURCE_GROUP" --location "$LOCATION" >/dev/null
fi

###########################################
# Step 2: Backend plan + webapp
###########################################

log "Ensuring backend App Service plan '$BACKEND_PLAN_NAME'..."
if ! az appservice plan show --name "$BACKEND_PLAN_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
  az appservice plan create \
    --name "$BACKEND_PLAN_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --sku "$BACKEND_PLAN_SKU" \
    --is-linux >/dev/null
fi

log "Ensuring backend webapp '$BACKEND_APP_NAME'..."
if ! az webapp show --name "$BACKEND_APP_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
  az webapp create \
    --name "$BACKEND_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --plan "$BACKEND_PLAN_NAME" \
    --runtime "$BACKEND_PYTHON_VERSION" >/dev/null
fi

log "Ensuring backend runtime stack: $BACKEND_PYTHON_VERSION"
az webapp config set \
  --name "$BACKEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --linux-fx-version "$BACKEND_PYTHON_VERSION" \
  >/dev/null

existing_run_from_mode="$(az webapp config appsettings list \
  --name "$BACKEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "[?name=='WEBSITE_RUN_FROM_PACKAGE' || name=='WEBSITE_RUN_FROM_ZIP'].value" \
  -o tsv || true)"
trimmed_existing="${existing_run_from_mode//[[:space:]]/}"
if [[ -n "$trimmed_existing" ]]; then
  if [[ "$BACKEND_RUN_FROM_PACKAGE" -eq 1 ]]; then
    log "Azure уже содержит WEBSITE_RUN_FROM_PACKAGE/ZIP. Сохраняем Run-From-Package (запрошено явно)."
    BACKEND_RUN_FROM_PACKAGE_EFFECTIVE=1
  else
    log "Azure уже содержит WEBSITE_RUN_FROM_PACKAGE/ZIP, но флаг --backend-run-from-package не задан. Сбрасываем эти настройки, чтобы позволить Oryx собрать зависимости (для сохранения режима передайте --backend-run-from-package)."
    BACKEND_RUN_FROM_PACKAGE_EFFECTIVE=0
  fi
else
  BACKEND_RUN_FROM_PACKAGE_EFFECTIVE="$BACKEND_RUN_FROM_PACKAGE"
fi

log "Ensuring backend startup command: $BACKEND_STARTUP_COMMAND"
az webapp config set \
  --name "$BACKEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --startup-file "$BACKEND_STARTUP_COMMAND" \
  >/dev/null

log "Removing deprecated backend app settings if present..."
deprecated_backend_settings=("PYTHONPATH")
if [[ "$BACKEND_RUN_FROM_PACKAGE_EFFECTIVE" -eq 0 ]]; then
  # Сбрасываем флаги Run-From-Package/Zip, иначе Azure пропускает Oryx build
  deprecated_backend_settings+=("WEBSITE_RUN_FROM_PACKAGE" "WEBSITE_RUN_FROM_ZIP")
fi

if [[ ${#deprecated_backend_settings[@]} -gt 0 ]]; then
  az webapp config appsettings delete \
    --name "$BACKEND_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --setting-names "${deprecated_backend_settings[@]}" \
    >/dev/null || true
fi

###########################################
# Step 3: Package backend and deploy
###########################################

log "Preparing backend deployment package..."
BACKEND_STAGE="$WORK_ROOT/backend_stage"
mkdir -p "$BACKEND_STAGE"
rsync -a --delete \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '*.pyo' \
  --exclude '*.pytest_cache' \
  --exclude '.mypy_cache' \
  --exclude 'build' \
  "$BACKEND_DIR/" "$BACKEND_STAGE/"

# Ensure runtime package always includes demo code allowlist under app/config.
DEMO_CODES_SOURCE="$BACKEND_DIR/config/demo_codes.json"
DEMO_CODES_TARGET="$BACKEND_STAGE/app/config/demo_codes.json"
if [[ -f "$DEMO_CODES_SOURCE" ]]; then
  mkdir -p "$(dirname "$DEMO_CODES_TARGET")"
  cp "$DEMO_CODES_SOURCE" "$DEMO_CODES_TARGET"
fi

if [[ -f "$BACKEND_STAGE/azure_startup.sh" ]]; then
  chmod +x "$BACKEND_STAGE/azure_startup.sh"
fi

BACKEND_REQ_FILE="$BACKEND_STAGE/requirements.txt"
python3 - <<'PY' "$BACKEND_DIR/pyproject.toml" "$BACKEND_REQ_FILE"
import sys
from pathlib import Path

pyproject_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])

deps = []
inside = False
for line in pyproject_path.read_text(encoding="utf-8").splitlines():
    stripped = line.strip()
    if not inside and stripped.startswith("dependencies") and stripped.endswith("["):
        inside = True
        continue
    if inside:
        if stripped.startswith("]"):
            break
        if not stripped or stripped.startswith("#"):
            continue
        stripped = stripped.rstrip(",")
        if stripped.startswith('"') and stripped.endswith('"'):
            stripped = stripped[1:-1]
        deps.append(stripped)

normalized = [d.split(">=")[0].split("==")[0] for d in deps]
if "gunicorn" not in normalized:
    deps.append("gunicorn>=21.2,<22.0")
if all(not d.startswith("pydantic-core") for d in deps):
    deps.append("pydantic-core>=2.18,<3.0")
if all(not d.startswith("cryptography") for d in deps):
    deps.append("cryptography>=41,<42")

if not deps:
    raise SystemExit("Не удалось определить зависимости из pyproject.toml")

output_path.write_text("\n".join(deps) + "\n", encoding="utf-8")
PY

log "Generated backend requirements.txt for Azure build pipeline."

backend_python_stack="${BACKEND_PYTHON_VERSION#PYTHON|}"
[[ "$backend_python_stack" == "$BACKEND_PYTHON_VERSION" ]] && backend_python_stack=""

BACKEND_PACKAGE="$WORK_ROOT/backend.zip"
BACKEND_PACKAGE_SRC="$(convert_path_for_az "$BACKEND_PACKAGE")"

BACKEND_ENV_SETTINGS=()

log "Collecting backend environment keys from '$BACKEND_CONFIG_FILE'..."
backend_env_keys_auto=()
while IFS= read -r key; do
  [[ -z "$key" ]] && continue
  backend_env_keys_auto+=("$key")
done < <(collect_backend_env_keys "$BACKEND_CONFIG_FILE")

BACKEND_ENV_KEYS_RAW="${!BACKEND_ENV_LIST_VAR-}"
backend_env_keys_manual=()
if [[ -n "$BACKEND_ENV_KEYS_RAW" ]]; then
  parse_key_list "$BACKEND_ENV_KEYS_RAW" backend_env_keys_manual
  if [[ ${#backend_env_keys_manual[@]} -gt 0 ]]; then
    log "Adding manual backend keys from $BACKEND_ENV_LIST_VAR: ${backend_env_keys_manual[*]}"
  fi
fi

combined_backend_env_keys=("${backend_env_keys_auto[@]}" "${backend_env_keys_manual[@]}")

if [[ ${#combined_backend_env_keys[@]} -gt 0 ]]; then
  unique_backend_keys=()
  for key in "${combined_backend_env_keys[@]}"; do
    [[ -z "$key" ]] && continue
    duplicate=0
    for seen_key in "${unique_backend_keys[@]}"; do
      if [[ "$seen_key" == "$key" ]]; then
        duplicate=1
        break
      fi
    done
    [[ $duplicate -eq 1 ]] && continue
    unique_backend_keys+=("$key")
  done

  log "Applying backend app settings from environment (unique keys: ${#unique_backend_keys[@]})..."

  applied_backend_settings=0
  for key in "${unique_backend_keys[@]}"; do
    if value="$(printenv "$key")"; then
      if ! should_skip_backend_env_setting "$key" "$value"; then
        BACKEND_ENV_SETTINGS+=("$key=$value")
        applied_backend_settings=$((applied_backend_settings + 1))
      fi
      continue
    fi

    manual_requested=0
    for manual_key in "${backend_env_keys_manual[@]}"; do
      if [[ "$manual_key" == "$key" ]]; then
        manual_requested=1
        break
      fi
    done

    if [[ $manual_requested -eq 1 ]]; then
      fail "Environment variable '$key' (referenced in $BACKEND_ENV_LIST_VAR) is not set."
    else
      # автособранные ключи пропускаем, если переменные отсутствуют
      continue
    fi
  done
  log "Applied $applied_backend_settings backend environment settings (plus defaults)."
else
  log "No backend environment keys detected; only default backend settings will be applied."
fi

if [[ "$BACKEND_RUN_FROM_PACKAGE_EFFECTIVE" -eq 1 ]]; then
  log "Run-From-Package включён: зависимости будут запакованы локально."
else
  log "Run-From-Package отключён: зависимости будут устанавливаться Oryx во время ZipDeploy."
fi

if [[ "$SKIP_KUDU_CLEANUP" -eq 1 ]]; then
  log "Пропускаем очистку .python_packages/antenv в Azure (SKIP_KUDU_CLEANUP=1). Убедитесь, что каталоги удалены вручную."
else
  log "Очищаем остатки Python окружения в Azure (через Kudu)..."
  if cleanup_remote_python_artifacts; then
    log "Удалены предыдущие каталоги .python_packages/antenv/output.tar.gz на сервере."
  else
    fail "Не удалось очистить удалённые зависимости через Kudu (rm -rf .python_packages/antenv/output.tar.gz). Повторите попытку после ручной очистки через Kudu/SSH или установите SKIP_KUDU_CLEANUP=1, если очистка уже проведена."
  fi
fi

deploy_attempt=1
current_backend_mode="$BACKEND_RUN_FROM_PACKAGE_EFFECTIVE"
backend_deps_installed=0

while :; do
  log "Deploying backend package (attempt $deploy_attempt, run_from_package=$current_backend_mode)..."

  if [[ "$current_backend_mode" -eq 1 && "$backend_deps_installed" -eq 0 ]]; then
    log "Installing backend dependencies into .python_packages (Run-From-Package mode)..."
    install_backend_dependencies "$BACKEND_STAGE" "$BACKEND_REQ_FILE" "$backend_python_stack"
    backend_deps_installed=1
  fi

  if [[ "$current_backend_mode" -eq 1 ]]; then
    prepare_run_from_package_tarball "$BACKEND_STAGE"
  else
    rm -f "$BACKEND_STAGE/output.tar.gz"
  fi

  rm -f "$BACKEND_PACKAGE"
  (
    cd "$BACKEND_STAGE"
    zip -qr "$BACKEND_PACKAGE" .
  )

  backend_control_settings=()
  if [[ "$current_backend_mode" -eq 1 ]]; then
    backend_control_settings+=(
      "SCM_DO_BUILD_DURING_DEPLOYMENT=false"
      "ENABLE_ORYX_BUILD=false"
      "WEBSITE_RUN_FROM_PACKAGE=1"
      "PYTHONPATH=/home/site/wwwroot:/home/site/wwwroot/.python_packages/lib/site-packages"
    )
  else
    backend_control_settings+=(
      "SCM_DO_BUILD_DURING_DEPLOYMENT=true"
      "ENABLE_ORYX_BUILD=true"
    )
  fi
  current_backend_settings=("${backend_control_settings[@]}" "${BACKEND_ENV_SETTINGS[@]}")

  az webapp config appsettings set \
    --name "$BACKEND_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --settings "${current_backend_settings[@]}" \
    >/dev/null

  log "Ожидаем применения настроек Azure (10s)..."
  sleep 10

  if [[ "$current_backend_mode" -eq 1 ]]; then
    log "Используем az webapp deploy (zip, без Oryx) для Run-From-Package."
    deploy_start_epoch="$(date +%s)"
    if az webapp deploy \
      --name "$BACKEND_APP_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --src-path "$BACKEND_PACKAGE_SRC" \
      --type zip \
      --ignore-stack true \
      --clean true \
      --track-status false \
      --restart true \
      >/dev/null; then
      if wait_for_kudu_deployment "$deploy_start_epoch"; then
        BACKEND_RUN_FROM_PACKAGE_EFFECTIVE=1
        break
      fi
      wait_status=$?
      if [[ "$wait_status" -eq 1 ]]; then
        log "Kudu OneDeploy сообщил об ошибке в Run-From-Package режиме. Попробуем ещё раз или завершим."
      else
        log "Не дождались завершения Kudu OneDeploy (Run-From-Package) за разумное время."
      fi
    elif kudu_deployment_succeeded_since "$deploy_start_epoch"; then
      log "az webapp deploy вернулся с ошибкой (например, 504), но Kudu OneDeploy завершился успешно в Run-From-Package режиме. Продолжаем."
      BACKEND_RUN_FROM_PACKAGE_EFFECTIVE=1
      break
    fi
  else
    log "Используем az webapp deploy для вызова Oryx build."
    deploy_start_epoch="$(date +%s)"
    if az webapp deploy \
      --name "$BACKEND_APP_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --src-path "$BACKEND_PACKAGE_SRC" \
      --type zip \
      --clean true \
      --track-status false \
      --restart true \
      >/dev/null; then
      if wait_for_kudu_deployment "$deploy_start_epoch"; then
        break
      fi
      wait_status=$?
      if [[ "$wait_status" -eq 1 ]]; then
        log "Kudu OneDeploy вернул ошибку, az webapp deploy будет повторён (или переключимся на Run-From-Package)."
      else
        log "Не дождались завершения Kudu OneDeploy за разумное время, az webapp deploy будет повторён."
      fi
    elif kudu_deployment_succeeded_since "$deploy_start_epoch"; then
      log "az webapp deploy завершился ошибкой (например, 504 GatewayTimeout), но Kudu сообщил об успешном OneDeploy. Продолжаем без переключения на Run-From-Package."
      break
    fi
  fi

  if [[ "$current_backend_mode" -eq 0 ]]; then
    log "Oryx deploy завершился с ошибкой, переключаемся на Run-From-Package и повторяем..."
    current_backend_mode=1
    BACKEND_RUN_FROM_PACKAGE_EFFECTIVE=1
    backend_deps_installed=0
    ((deploy_attempt++))
    continue
  fi

  fail "Backend deployment failed даже в Run-From-Package режиме. Проверьте логи Kudu/ZipDeploy."
done

log "Backend package deployed successfully."

BACKEND_HOSTNAME="https://${BACKEND_APP_NAME}.azurewebsites.net"

###########################################
# Step 4: oauth2-proxy plan + webapp
###########################################

if [[ "$OAUTH_PLAN_NAME" != "$BACKEND_PLAN_NAME" ]]; then
  log "Ensuring oauth2-proxy App Service plan '$OAUTH_PLAN_NAME'..."
  if ! az appservice plan show --name "$OAUTH_PLAN_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
    az appservice plan create \
      --name "$OAUTH_PLAN_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --location "$LOCATION" \
      --sku "$OAUTH_PLAN_SKU" \
      --is-linux >/dev/null
  fi
fi

log "Ensuring oauth2-proxy webapp '$OAUTH_APP_NAME'..."
if ! az webapp show --name "$OAUTH_APP_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
  az webapp create \
    --name "$OAUTH_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --plan "$OAUTH_PLAN_NAME" \
    --deployment-container-image-name "$OAUTH_IMAGE" \
    >/dev/null
fi

log "Updating oauth2-proxy container configuration..."
az webapp config container set \
  --name "$OAUTH_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --docker-custom-image-name "$OAUTH_IMAGE" \
  >/dev/null

OAUTH_SETTINGS=("WEBSITES_PORT=$OAUTH_CONTAINER_PORT")
if [[ -n "$OAUTH_ENV_FILE" ]]; then
  log "Applying oauth2-proxy settings from '$OAUTH_ENV_FILE'..."
  read_settings_file "$OAUTH_ENV_FILE" oauth_env_settings
  OAUTH_SETTINGS+=("${oauth_env_settings[@]}")
fi

az webapp config appsettings set \
  --name "$OAUTH_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --settings "${OAUTH_SETTINGS[@]}" \
  >/dev/null

OAUTH_HOSTNAME="https://${OAUTH_APP_NAME}.azurewebsites.net"

###########################################
# Step 5: Build frontend
###########################################

log "Installing frontend dependencies via npm ci..."
(cd "$FRONTEND_DIR" && npm ci >/dev/null)

if [[ -z "$FRONTEND_API_URL" ]]; then
  if [[ -n "${VITE_API_BASE_URL:-}" ]]; then
    FRONTEND_API_URL="$VITE_API_BASE_URL"
  else
    FRONTEND_API_URL="$BACKEND_HOSTNAME"
  fi
fi

log "Building frontend with VITE_API_BASE_URL='$FRONTEND_API_URL'..."
build_env=()
if [[ -n "$FRONTEND_API_URL" ]]; then
  build_env+=("VITE_API_BASE_URL=$FRONTEND_API_URL")
fi
if [[ ${#build_env[@]} -gt 0 ]]; then
  (cd "$FRONTEND_DIR" && env "${build_env[@]}" npm run build >/dev/null)
else
  (cd "$FRONTEND_DIR" && npm run build >/dev/null)
fi

if [[ ! -d "$DIST_DIR" ]]; then
  fail "Frontend build output not found at '$DIST_DIR'."
fi

###########################################
# Step 6: Static Web App provisioning + upload
###########################################

log "Ensuring Static Web App '$FRONTEND_APP_NAME'..."
if ! az staticwebapp show --name "$FRONTEND_APP_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
  az staticwebapp create \
    --name "$FRONTEND_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --sku "$FRONTEND_SWA_SKU" \
    >/dev/null
fi

DEPLOYMENT_TOKEN="$(az staticwebapp secrets list --name "$FRONTEND_APP_NAME" --resource-group "$RESOURCE_GROUP" --query 'properties.apiKey' -o tsv)"
[[ -z "$DEPLOYMENT_TOKEN" ]] && fail "Failed to retrieve deployment token for Static Web App."

FRONTEND_DEFAULT_HOSTNAME="$(az staticwebapp show --name "$FRONTEND_APP_NAME" --resource-group "$RESOURCE_GROUP" --query 'defaultHostname' -o tsv)"
[[ -z "$FRONTEND_DEFAULT_HOSTNAME" ]] && fail "Failed to determine Static Web App hostname."
FRONTEND_BASE_URL="https://${FRONTEND_DEFAULT_HOSTNAME}"

log "Uploading frontend package to Static Web App via swa deploy (${SWA_DEPLOY_PACKAGE}, env=${SWA_DEPLOY_ENVIRONMENT})..."
SWA_DEPLOY_LOG="$WORK_ROOT/swa_deploy.log"
set +e
SWA_CLI_DEPLOYMENT_TOKEN="$DEPLOYMENT_TOKEN" npx --yes "$SWA_DEPLOY_PACKAGE" deploy "$DIST_DIR" --env "$SWA_DEPLOY_ENVIRONMENT" 2>&1 | tee "$SWA_DEPLOY_LOG"
SWA_DEPLOY_EXIT=${PIPESTATUS[0]}
set -e
if [[ "$SWA_DEPLOY_EXIT" -ne 0 ]]; then
  log "Static Web App deployment failed. Inspect '$SWA_DEPLOY_LOG' for details."
  fail "Failed to deploy frontend via swa deploy (exit code $SWA_DEPLOY_EXIT)."
fi

FRONTEND_HOSTNAME="$FRONTEND_BASE_URL"

###########################################
# Step 7: Output summary
###########################################

echo ""
echo "Deployment completed successfully."
echo "Frontend: ${FRONTEND_HOSTNAME}"
echo "Backend : ${BACKEND_HOSTNAME}"
echo "oauth2  : ${OAUTH_HOSTNAME}"
echo ""
log "All resources provisioned. Remember to configure database, storage, and other dependencies as needed."
