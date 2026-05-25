#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="${ROOT_DIR}/.venv/Scripts/python.exe"

if [[ ! -x "${VENV_PY}" ]]; then
  echo "Missing virtual environment at .venv"
  exit 1
fi

cd "${ROOT_DIR}"

"${VENV_PY}" -m pip install -r requirements.txt
"${VENV_PY}" -m pytest -v --cov
"${VENV_PY}" -m compileall src

if command -v docker >/dev/null 2>&1; then
  DOCKER_COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  DOCKER_COMPOSE=(docker-compose)
else
  echo "Docker Compose is not available on this machine"
  exit 1
fi

"${DOCKER_COMPOSE[@]}" build
"${DOCKER_COMPOSE[@]}" up -d

"${VENV_PY}" - <<'PY'
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)
health = client.get('/health')
assert health.status_code == 200, health.text
assert health.json()['status'] == 'healthy'

auth = client.post('/auth/token', data={'username': 'admin', 'password': 'admin123'})
assert auth.status_code == 200, auth.text
assert 'access_token' in auth.json()

print('API validation passed')
PY

"${VENV_PY}" - <<'PY'
from src.simulation.environment import RetailSimulator
import asyncio

async def main():
    sim = RetailSimulator(seed=42)
    metrics = await sim.run(1)
    assert 'revenue' in metrics
    assert 'profit' in metrics
    print('Simulation validation passed')

asyncio.run(main())
PY

echo "Full validation completed"
