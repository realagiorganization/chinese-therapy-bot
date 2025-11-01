#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${ROOT_DIR}/.mindwell/agents"
LOG_DIR="${STATE_DIR}/logs"
mkdir -p "${LOG_DIR}"

declare -A AGENT_MODULES=(
  ["summary-scheduler"]="app.agents.summary_scheduler"
  ["data-sync"]="app.agents.data_sync"
  ["retention-cleanup"]="app.agents.retention_cleanup"
)

function usage() {
  cat <<'EOF'
Usage: scripts/agent-control.sh <command> [agent|all]

Commands:
  start     Start the specified agent (or all agents) in the background.
  stop      Stop the specified agent (or all agents) if running.
  restart   Restart the specified agent (or all agents).
  status    Print status information for the specified agent (or all agents).
  logs      Tail the log for the specified agent (defaults to last 100 lines).
  list      List all known agents.
  help      Show this message.

Agents:
  summary-scheduler   Generates daily/weekly summaries.
  data-sync           Normalizes therapist roster data.
  retention-cleanup   Enforces transcript/summary retention policies.

Environment overrides:
  MINDWELL_VENV   Path to virtualenv containing project dependencies.
  MINDWELL_PYTHON Path to python executable (overrides autodetection).
  MINDWELL_LOG_LINES Number of lines to show for "logs" command (default: 100).
EOF
}

function ensure_python() {
  if [[ -n "${MINDWELL_PYTHON:-}" ]]; then
    if [[ ! -x "${MINDWELL_PYTHON}" ]]; then
      echo "Specified MINDWELL_PYTHON is not executable: ${MINDWELL_PYTHON}" >&2
      exit 1
    fi
    PYTHON_BIN="${MINDWELL_PYTHON}"
    return
  fi

  if [[ -n "${MINDWELL_VENV:-}" ]]; then
    local candidate="${MINDWELL_VENV%/}/bin/python"
    if [[ -x "${candidate}" ]]; then
      PYTHON_BIN="${candidate}"
      return
    fi
  fi

  local candidate="${ROOT_DIR}/services/backend/.venv/bin/python"
  if [[ -x "${candidate}" ]]; then
    PYTHON_BIN="${candidate}"
    return
  fi

  candidate="${ROOT_DIR}/.venv/bin/python"
  if [[ -x "${candidate}" ]]; then
    PYTHON_BIN="${candidate}"
    return
  fi

  candidate="$(command -v python3 || true)"
  if [[ -n "${candidate}" ]]; then
    PYTHON_BIN="${candidate}"
    return
  fi

  candidate="$(command -v python || true)"
  if [[ -n "${candidate}" ]]; then
    PYTHON_BIN="${candidate}"
    return
  fi

  echo "Unable to locate a python executable. Set MINDWELL_PYTHON explicitly." >&2
  exit 1
}

function agent_exists() {
  local agent="$1"
  [[ -n "${AGENT_MODULES[$agent]+x}" ]]
}

function pid_file_for() {
  local agent="$1"
  echo "${STATE_DIR}/${agent}.pid"
}

function log_file_for() {
  local agent="$1"
  echo "${LOG_DIR}/${agent}.log"
}

function is_running() {
  local agent="$1"
  local pid_file
  pid_file="$(pid_file_for "${agent}")"
  if [[ ! -f "${pid_file}" ]]; then
    return 1
  fi
  local pid
  pid="$(<"${pid_file}")"
  if [[ -z "${pid}" ]]; then
    return 1
  fi
  if kill -0 "${pid}" 2>/dev/null; then
    return 0
  fi
  rm -f "${pid_file}"
  return 1
}

function start_agent() {
  local agent="$1"
  local module="${AGENT_MODULES[$agent]}"
  local pid_file
  pid_file="$(pid_file_for "${agent}")"
  local log_file
  log_file="$(log_file_for "${agent}")"

  if is_running "${agent}"; then
    echo "[${agent}] already running (pid $(<"${pid_file}"))."
    return
  fi

  echo "[${agent}] starting..."
  (
    cd "${ROOT_DIR}/services/backend"
    export PYTHONPATH="${ROOT_DIR}/services/backend:${PYTHONPATH:-}"
    ensure_python
    nohup "${PYTHON_BIN}" -m "${module}" >>"${log_file}" 2>&1 &
    local pid=$!
    echo "${pid}" > "${pid_file}"
  )
  sleep 0.5
  if is_running "${agent}"; then
    echo "[${agent}] started (pid $(<"${pid_file}")). Logs: ${log_file}"
  else
    echo "[${agent}] failed to start. Check logs at ${log_file}" >&2
    exit 1
  fi
}

function stop_agent() {
  local agent="$1"
  local pid_file
  pid_file="$(pid_file_for "${agent}")"
  if ! is_running "${agent}"; then
    echo "[${agent}] not running."
    return
  fi

  local pid
  pid="$(<"${pid_file}")"
  echo "[${agent}] stopping (pid ${pid})..."
  if ! kill "${pid}" 2>/dev/null; then
    echo "[${agent}] failed to send SIGTERM to pid ${pid}." >&2
    rm -f "${pid_file}"
    return
  fi

  local waited=0
  local timeout=15
  while kill -0 "${pid}" 2>/dev/null; do
    sleep 1
    waited=$((waited + 1))
    if [[ ${waited} -ge ${timeout} ]]; then
      echo "[${agent}] did not exit after ${timeout}s; sending SIGKILL."
      kill -9 "${pid}" 2>/dev/null || true
      break
    fi
  done

  rm -f "${pid_file}"
  echo "[${agent}] stopped."
}

function status_agent() {
  local agent="$1"
  local pid_file
  pid_file="$(pid_file_for "${agent}")"
  if is_running "${agent}"; then
    echo "[${agent}] running (pid $(<"${pid_file}")). Log: $(log_file_for "${agent}")"
  else
    echo "[${agent}] not running."
  fi
}

function tail_logs() {
  local agent="$1"
  local log_file
  log_file="$(log_file_for "${agent}")"
  local lines="${MINDWELL_LOG_LINES:-100}"

  if [[ ! -f "${log_file}" ]]; then
    echo "No log file found for ${agent} at ${log_file}."
    return
  fi
  tail -n "${lines}" "${log_file}"
}

function list_agents() {
  echo "Known agents:"
  for agent in "${!AGENT_MODULES[@]}"; do
    echo "  - ${agent}"
  done | sort
}

function expand_targets() {
  local target="$1"
  if [[ "${target}" == "all" ]]; then
    printf "%s\n" "${!AGENT_MODULES[@]}" | sort
  else
    echo "${target}"
  fi
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

command="$1"
target="${2:-all}"

case "${command}" in
  help|--help|-h)
    usage
    exit 0
    ;;
  list)
    list_agents
    exit 0
    ;;
  start|stop|restart|status|logs)
    ;;
  *)
    echo "Unknown command: ${command}" >&2
    usage
    exit 1
    ;;
esac

readarray -t agents <<<"$(expand_targets "${target}")"
if [[ ${#agents[@]} -eq 0 ]]; then
  echo "No agents resolved from target '${target}'." >&2
  exit 1
fi

for agent in "${agents[@]}"; do
  if ! agent_exists "${agent}"; then
    echo "Unknown agent '${agent}'." >&2
    echo "Run 'scripts/agent-control.sh list' to see valid agents." >&2
    exit 1
  fi
done

case "${command}" in
  start)
    for agent in "${agents[@]}"; do
      start_agent "${agent}"
    done
    ;;
  stop)
    for agent in "${agents[@]}"; do
      stop_agent "${agent}"
    done
    ;;
  restart)
    for agent in "${agents[@]}"; do
      stop_agent "${agent}"
      start_agent "${agent}"
    done
    ;;
  status)
    for agent in "${agents[@]}"; do
      status_agent "${agent}"
    done
    ;;
  logs)
    if [[ ${#agents[@]} -ne 1 ]]; then
      echo "The logs command requires a single agent target." >&2
      exit 1
    fi
    tail_logs "${agents[0]}"
    ;;
esac
