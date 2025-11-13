#!/bin/sh
set -euo pipefail

/usr/local/bin/oauth2-proxy --config=/etc/oauth2-proxy.cfg &
OAUTH_PID=$!

term_handler() {
  kill -TERM "$OAUTH_PID" 2>/dev/null
  wait "$OAUTH_PID"
}

trap term_handler INT TERM

exec caddy run --config /etc/caddy/Caddyfile
