#!/usr/bin/env bash
set -euo pipefail

ROOT_REPO="${1:-$(git rev-parse --show-toplevel)}"
WORK_DIR="$(mktemp -d)"
CLONE_DIR="${WORK_DIR}/retail-multi-agent-ai"
API_PID=""

cleanup() {
  if [[ -n "${API_PID}" ]] && kill -0 "${API_PID}" >/dev/null 2>&1; then
    kill "${API_PID}" >/dev/null 2>&1 || true
    wait "${API_PID}" >/dev/null 2>&1 || true
  fi
  rm -rf "${WORK_DIR}"
}

trap cleanup EXIT

git clone "${ROOT_REPO}" "${CLONE_DIR}"
cd "${CLONE_DIR}"

if command -v powershell.exe >/dev/null 2>&1; then
  WINDOWS_PYTHON="$(powershell.exe -NoProfile -Command "(Get-Command python.exe -ErrorAction SilentlyContinue).Source" | tr -d '\r')"
  if [[ -n "${WINDOWS_PYTHON}" && -x "${WINDOWS_PYTHON}" ]]; then
    PYTHON_CMD=("${WINDOWS_PYTHON}")
  fi
fi

if [[ -z "${PYTHON_CMD[*]:-}" ]]; then
  if command -v py >/dev/null 2>&1; then
    PYTHON_CMD=(py -3)
  elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD=(python)
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD=(python3)
  else
    echo "Python is not available on this machine"
    exit 1
  fi
fi

"${PYTHON_CMD[@]}" -m venv .venv
if [[ -x .venv/bin/python ]]; then
  VENV_PY=".venv/bin/python"
else
  VENV_PY=".venv/Scripts/python.exe"
fi

"${VENV_PY}" -m pip install --upgrade pip
"${VENV_PY}" -m pip install -r requirements.txt
"${VENV_PY}" -m pytest -v --cov --cov-fail-under=80 --cov-report=term-missing --cov-report=xml:coverage.xml --cov-report=html:htmlcov
"${VENV_PY}" -m compileall src

API_LOG="${WORK_DIR}/api.log"
"${VENV_PY}" -m src.api.main >"${API_LOG}" 2>&1 &
API_PID=$!

"${VENV_PY}" - <<'PY'
import json
import os
import sys
import time
from urllib.request import urlopen

for _ in range(60):
    try:
        with urlopen("http://127.0.0.1:8000/health", timeout=1) as response:
            payload = json.load(response)
        assert payload["status"] == "healthy"
        print("API health check passed")
        sys.exit(0)
    except Exception:
        time.sleep(1)

raise SystemExit("API health endpoint did not become ready")
PY

SIM_OUTPUT="$("${VENV_PY}" -m src.simulation.run_simulation --days 1 --seed 42)"
case "${SIM_OUTPUT}" in
  *revenue*profit*|*profit*revenue*)
    printf '%s\n' "${SIM_OUTPUT}"
    ;;
  *)
    printf '%s\n' "${SIM_OUTPUT}"
    echo "Simulation output did not include expected metrics"
    exit 1
    ;;
esac

echo "Fresh clone validation passed"