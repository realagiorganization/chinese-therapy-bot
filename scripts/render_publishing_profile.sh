#!/usr/bin/env bash
set -euo pipefail

TEMPLATE_PATH="${1:-publishing_profiles.json}"
OUTPUT_PATH="${2:-publishing_profiles.secrets.json}"

PASSWORD="${MINDWELL_PUBLISHING_PROFILE_PASSWORD:-}"
if [[ -z "$PASSWORD" ]]; then
  echo "ERROR: Set MINDWELL_PUBLISHING_PROFILE_PASSWORD before running this script." >&2
  exit 1
fi

python - <<'PY' "$TEMPLATE_PATH" "$OUTPUT_PATH" "$PASSWORD"
import json
import pathlib
import sys

template_path = pathlib.Path(sys.argv[1])
output_path = pathlib.Path(sys.argv[2])
password = sys.argv[3]

if not template_path.exists():
    raise SystemExit(f"Template file '{template_path}' not found.")

with template_path.open("r", encoding="utf-8") as fh:
    data = json.load(fh)

if not isinstance(data, list):
    raise SystemExit("Template JSON must contain a list of publishing profiles.")

for profile in data:
    profile["userPWD"] = password

output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
print(f"Wrote {output_path} with {len(data)} profiles.")
PY

chmod 600 "$OUTPUT_PATH"
echo "Done. Provide '$OUTPUT_PATH' to Azure tooling that expects the real publishing profile."
