#!/usr/bin/env bash
set -euo pipefail
python -c "from src.core.database import init_db; init_db(); print('Database initialized')"
