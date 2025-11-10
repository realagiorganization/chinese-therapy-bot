#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$SCRIPT_DIR"
ANTENV_DIR="$APP_ROOT/antenv"

# If the site is configured with WEBSITE_RUN_FROM_PACKAGE, Azure may invoke this
# script from the mutable /home/site/wwwroot copy that no longer includes the
# packaged dependencies. In that case, re-extract the active SitePackages ZIP
# into /tmp and restart the script from the extracted location so that
# .python_packages is guaranteed to exist.
PACKAGE_NAME_FILE="/home/data/SitePackages/packagename.txt"
RUN_FROM_PACKAGE_ROOT="$APP_ROOT/.python_packages/lib/site-packages"
if [[ ! -d "$RUN_FROM_PACKAGE_ROOT" && -f "$PACKAGE_NAME_FILE" ]]; then
  package_basename="$(<"$PACKAGE_NAME_FILE")"
  package_zip="/home/data/SitePackages/${package_basename}"
  if [[ -n "$package_basename" && -f "$package_zip" ]]; then
    tmp_app_dir="$(mktemp -d /tmp/mindwell-app-XXXXXX)"
    if unzip -q "$package_zip" -d "$tmp_app_dir"; then
      echo "azure_startup: .python_packages отсутствует в ${APP_ROOT}, перезапускаем из ${tmp_app_dir}" >&2
      exec "$tmp_app_dir/azure_startup.sh" "$@"
    else
      echo "azure_startup: не удалось распаковать ${package_zip}" >&2
    fi
  fi
fi

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

exec gunicorn -k uvicorn.workers.UvicornWorker \
  --bind="0.0.0.0:${PORT:-8000}" \
  app.main:app
