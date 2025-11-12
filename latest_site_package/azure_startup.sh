#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/home/site/wwwroot"
ANTENV_DIR="$APP_ROOT/antenv"

normalize_timeout() {
  local raw="$1"
  local fallback="$2"
  if [[ "$raw" =~ ^[0-9]+$ ]]; then
    printf '%s\n' "$raw"
  else
    printf '%s\n' "$fallback"
  fi
}

# When Oryx performs the build it creates a virtualenv (antenv); make sure we
# activate it so gunicorn sees all packages just like the stock startup script.
if [[ -f "$ANTENV_DIR/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ANTENV_DIR/bin/activate"
fi

# Azure App Service mounts a read-only filesystem at /home/site/wwwroot.
# Dependencies that we package via Run‑From‑Package live under .python_packages.
# Make sure that directory (and the app root itself) are always on PYTHONPATH
# before we spawn gunicorn so imports like pydantic_core/uvicorn succeed even
# when Oryx skips rebuilding the environment.
PYTHONPATH_BUILDER=(
  "$APP_ROOT"
  "$APP_ROOT/.python_packages/lib/site-packages"
)

if [[ -d "$ANTENV_DIR/lib" ]]; then
  while IFS= read -r -d '' site_packages; do
    PYTHONPATH_BUILDER+=("$site_packages")
  done < <(find "$ANTENV_DIR/lib" -maxdepth 2 -type d -name 'site-packages' -print0 2>/dev/null)
fi

for candidate in "${PYTHONPATH_BUILDER[@]}"; do
  if [[ -d "$candidate" ]]; then
    if [[ -z "${PYTHONPATH:-}" ]]; then
      PYTHONPATH="$candidate"
    else
      PYTHONPATH="$candidate:$PYTHONPATH"
    fi
  fi
done

export PYTHONPATH
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"

DATABASE_MIGRATION_TIMEOUT="$(normalize_timeout "${DATABASE_MIGRATION_TIMEOUT:-}" 120)"
export DATABASE_MIGRATION_TIMEOUT

GUNICORN_TIMEOUT="$(normalize_timeout "${GUNICORN_TIMEOUT:-}" 90)"
MIN_GUNICORN_TIMEOUT=180
if (( GUNICORN_TIMEOUT < DATABASE_MIGRATION_TIMEOUT || GUNICORN_TIMEOUT < MIN_GUNICORN_TIMEOUT )); then
  local_timeout_buffer=$((DATABASE_MIGRATION_TIMEOUT + 30))
  if (( local_timeout_buffer < MIN_GUNICORN_TIMEOUT )); then
    local_timeout_buffer=$MIN_GUNICORN_TIMEOUT
  fi
  echo "azure_startup: увеличиваем GUNICORN_TIMEOUT с ${GUNICORN_TIMEOUT}s до ${local_timeout_buffer}s (DATABASE_MIGRATION_TIMEOUT=${DATABASE_MIGRATION_TIMEOUT}s)" >&2
  GUNICORN_TIMEOUT="$local_timeout_buffer"
fi

exec gunicorn -k uvicorn.workers.UvicornWorker \
  --bind="0.0.0.0:${PORT:-8000}" \
  --timeout="${GUNICORN_TIMEOUT}" \
  app.main:app
