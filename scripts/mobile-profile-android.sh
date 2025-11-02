#!/usr/bin/env bash

set -euo pipefail

# Profile the Android bundle size for the Expo client. Produces a release-style
# bundle and reports raw/gzip sizes to help tune startup on mid-range devices.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="${ROOT_DIR}/clients/mobile"
OUTPUT_DIR="${APP_DIR}/dist/profile-android"

echo "[profile-android] Cleaning ${OUTPUT_DIR}"
rm -rf "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}/assets"

pushd "${APP_DIR}" > /dev/null

echo "[profile-android] Bundling release artifacts"
npx react-native bundle \
  --platform android \
  --dev false \
  --entry-file index.js \
  --bundle-output "${OUTPUT_DIR}/index.android.bundle" \
  --assets-dest "${OUTPUT_DIR}/assets" \
  --reset-cache

echo "[profile-android] Calculating bundle sizes"
RAW_SIZE=$(stat --format="%s" "${OUTPUT_DIR}/index.android.bundle")
GZIP_SIZE=$(gzip -c "${OUTPUT_DIR}/index.android.bundle" | wc -c)

echo "Bundle (raw): ${RAW_SIZE} bytes"
echo "Bundle (gzip): ${GZIP_SIZE} bytes"

ASSET_TOTAL_RAW=0
ASSET_TOTAL_GZIP=0
while IFS= read -r -d '' asset; do
  SIZE=$(stat --format="%s" "${asset}")
  GZIP=$(gzip -c "${asset}" | wc -c)
  ASSET_TOTAL_RAW=$((ASSET_TOTAL_RAW + SIZE))
  ASSET_TOTAL_GZIP=$((ASSET_TOTAL_GZIP + GZIP))
done < <(find "${OUTPUT_DIR}/assets" -type f -print0)

echo "Assets (raw): ${ASSET_TOTAL_RAW} bytes"
echo "Assets (gzip): ${ASSET_TOTAL_GZIP} bytes"

popd > /dev/null

echo "[profile-android] Complete. Output stored under ${OUTPUT_DIR}"
