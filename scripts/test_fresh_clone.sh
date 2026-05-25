#!/usr/bin/env bash
set -u -o pipefail

ROOT_REPO="${1:-$(git rev-parse --show-toplevel)}"
WORK_DIR="$(mktemp -d)"
CLONE_DIR="${WORK_DIR}/retail-multi-agent-ai"
REPORT_PATH="${ROOT_REPO}/FRESH_CLONE_REPORT.md"
API_PID=""
DASHBOARD_PID=""

TIMESTAMP=""
OS_INFO=""
PYTHON_VERSION=""
COVERAGE_PERCENT="n/a"
DEPENDENCY_STATUS="FAIL"
PYTEST_STATUS="FAIL"
COVERAGE_STATUS="FAIL"
COMPILEALL_STATUS="FAIL"
AUTH_STATUS="FAIL"
API_STATUS="FAIL"
SIMULATION_STATUS="FAIL"
DASHBOARD_STATUS="FAIL"
SIM_EXIT_CODE="n/a"
SIM_STDOUT=""
SIM_STDERR=""

cleanup() {
  if [[ -n "${API_PID}" ]] && kill -0 "${API_PID}" >/dev/null 2>&1; then
    kill "${API_PID}" >/dev/null 2>&1 || true
    wait "${API_PID}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${DASHBOARD_PID}" ]] && kill -0 "${DASHBOARD_PID}" >/dev/null 2>&1; then
    kill "${DASHBOARD_PID}" >/dev/null 2>&1 || true
    wait "${DASHBOARD_PID}" >/dev/null 2>&1 || true
  fi
  rm -rf "${WORK_DIR}"
}

write_report() {
  local fresh_clone_verified="NO"
  if [[ "${DEPENDENCY_STATUS}" == "PASS" && "${PYTEST_STATUS}" == "PASS" && "${COVERAGE_STATUS}" == "PASS" && "${COMPILEALL_STATUS}" == "PASS" && "${AUTH_STATUS}" == "PASS" && "${API_STATUS}" == "PASS" && "${SIMULATION_STATUS}" == "PASS" && "${DASHBOARD_STATUS}" == "PASS" ]]; then
    fresh_clone_verified="YES"
  fi

  REPORT_PATH_ENV="${REPORT_PATH}" TIMESTAMP_ENV="${TIMESTAMP}" OS_INFO_ENV="${OS_INFO}" PYTHON_VERSION_ENV="${PYTHON_VERSION}" COVERAGE_PERCENT_ENV="${COVERAGE_PERCENT}" DEPENDENCY_STATUS_ENV="${DEPENDENCY_STATUS}" PYTEST_STATUS_ENV="${PYTEST_STATUS}" COVERAGE_STATUS_ENV="${COVERAGE_STATUS}" COMPILEALL_STATUS_ENV="${COMPILEALL_STATUS}" AUTH_STATUS_ENV="${AUTH_STATUS}" API_STATUS_ENV="${API_STATUS}" SIMULATION_STATUS_ENV="${SIMULATION_STATUS}" DASHBOARD_STATUS_ENV="${DASHBOARD_STATUS}" FRESH_CLONE_VERIFIED_ENV="${fresh_clone_verified}" SIM_EXIT_CODE_ENV="${SIM_EXIT_CODE}" SIM_STDOUT_ENV="${SIM_STDOUT}" SIM_STDERR_ENV="${SIM_STDERR}" python - <<'PY'
from pathlib import Path
import os

report_path = Path(os.environ["REPORT_PATH_ENV"])
content = f"""# Fresh Clone Report

- Timestamp (UTC): {os.environ['TIMESTAMP_ENV']}
- OS: {os.environ['OS_INFO_ENV']}
- Python version: {os.environ['PYTHON_VERSION_ENV']}
- Dependency install: {os.environ['DEPENDENCY_STATUS_ENV']}
- Pytest: {os.environ['PYTEST_STATUS_ENV']}
- Coverage: {os.environ['COVERAGE_PERCENT_ENV']}
- Compileall: {os.environ['COMPILEALL_STATUS_ENV']}
- Auth: {os.environ['AUTH_STATUS_ENV']}
- API: {os.environ['API_STATUS_ENV']}
- Simulation: {os.environ['SIMULATION_STATUS_ENV']}
- Dashboard: {os.environ['DASHBOARD_STATUS_ENV']}

## Final

- Fresh clone verified: {os.environ['FRESH_CLONE_VERIFIED_ENV']}

## Simulation Capture

- Exit code: {os.environ['SIM_EXIT_CODE_ENV']}

### stdout

```text
{os.environ['SIM_STDOUT_ENV']}
```

### stderr

```text
{os.environ['SIM_STDERR_ENV']}
```
"""
report_path.write_text(content, encoding="utf-8")
PY
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
    write_report
    exit 1
  fi
fi

"${PYTHON_CMD[@]}" -m venv .venv
if [[ -x .venv/bin/python ]]; then
  VENV_PY=".venv/bin/python"
else
  VENV_PY=".venv/Scripts/python.exe"
fi

TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
OS_INFO="$(uname -a 2>/dev/null || echo 'unknown')"
PYTHON_VERSION="$(${VENV_PY} --version 2>&1)"

if "${VENV_PY}" -m pip install --upgrade pip && "${VENV_PY}" -m pip install -r requirements.txt; then
  DEPENDENCY_STATUS="PASS"
fi

if [[ "${DEPENDENCY_STATUS}" == "PASS" ]]; then
  if "${VENV_PY}" -m pytest -v --cov --cov-fail-under=80 --cov-report=term-missing --cov-report=xml:coverage.xml --cov-report=html:htmlcov; then
    PYTEST_STATUS="PASS"
    COVERAGE_STATUS="PASS"
    COVERAGE_PERCENT="$(${VENV_PY} - <<'PY'
from pathlib import Path
import subprocess
import sys

result = subprocess.run([sys.executable, "-m", "coverage", "report"], capture_output=True, text=True, check=True)
for line in result.stdout.splitlines():
    if line.startswith("TOTAL"):
        print(line.split()[-1])
        raise SystemExit(0)
raise SystemExit("coverage total not found")
PY
)"
  fi
fi

if [[ "${PYTEST_STATUS}" == "PASS" ]]; then
  if "${VENV_PY}" -m compileall src; then
    COMPILEALL_STATUS="PASS"
  fi
fi

if [[ "${COMPILEALL_STATUS}" == "PASS" ]]; then
  if "${VENV_PY}" - <<'PY'
from src.api.auth import authenticate_user, create_access_token, decode_access_token

token = create_access_token({"sub": "admin"})
assert decode_access_token(token)["sub"] == "admin"
assert authenticate_user("admin", "admin123") is not None
print("auth-ok")
PY
  then
    AUTH_STATUS="PASS"
  fi
fi

API_LOG="${WORK_DIR}/api.log"
if [[ "${AUTH_STATUS}" == "PASS" ]]; then
  "${VENV_PY}" -m src.api.main >"${API_LOG}" 2>&1 &
  API_PID=$!

  if "${VENV_PY}" - <<'PY'
import json
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
  then
    API_STATUS="PASS"
  fi
fi

DASHBOARD_LOG="${WORK_DIR}/dashboard.log"
if [[ "${API_STATUS}" == "PASS" ]]; then
  "${VENV_PY}" -m streamlit run src/dashboard/app.py --server.headless true --server.port 8502 --browser.gatherUsageStats false >"${DASHBOARD_LOG}" 2>&1 &
  DASHBOARD_PID=$!

  if "${VENV_PY}" - <<'PY'
import sys
import time
from urllib.request import urlopen

for _ in range(60):
    try:
        with urlopen("http://127.0.0.1:8502/_stcore/health", timeout=1) as response:
            body = response.read().decode("utf-8", errors="replace").strip().lower()
        assert body == "ok"
        print("Dashboard health check passed")
        sys.exit(0)
    except Exception:
        time.sleep(1)

raise SystemExit("Dashboard health endpoint did not become ready")
PY
  then
    DASHBOARD_STATUS="PASS"
  fi
fi

SIM_STDOUT_FILE="${WORK_DIR}/simulation.stdout"
SIM_STDERR_FILE="${WORK_DIR}/simulation.stderr"
if [[ "${DASHBOARD_STATUS}" == "PASS" ]]; then
  set +e
  "${VENV_PY}" -m src.simulation.run_simulation --days 1 --seed 42 >"${SIM_STDOUT_FILE}" 2>"${SIM_STDERR_FILE}"
  SIM_EXIT_CODE=$?
  set -e

  SIM_STDOUT="$(cat "${SIM_STDOUT_FILE}" 2>/dev/null || true)"
  SIM_STDERR="$(cat "${SIM_STDERR_FILE}" 2>/dev/null || true)"

  if [[ "${SIM_EXIT_CODE}" -eq 0 ]]; then
    case "${SIM_STDOUT}" in
      *revenue*profit*|*profit*revenue*|*fill_rate*stockout_rate*on_time_delivery_rate*|*on_time_delivery_rate*stockout_rate*fill_rate*)
        SIMULATION_STATUS="PASS"
        ;;
    esac
  fi
fi

write_report

if [[ "${DEPENDENCY_STATUS}" != "PASS" || "${PYTEST_STATUS}" != "PASS" || "${COVERAGE_STATUS}" != "PASS" || "${COMPILEALL_STATUS}" != "PASS" || "${AUTH_STATUS}" != "PASS" || "${API_STATUS}" != "PASS" || "${SIMULATION_STATUS}" != "PASS" || "${DASHBOARD_STATUS}" != "PASS" ]]; then
  echo "Fresh clone validation failed"
  exit 1
fi

echo "Fresh clone validation passed"