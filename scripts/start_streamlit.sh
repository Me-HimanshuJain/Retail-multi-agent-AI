#!/usr/bin/env bash
# Start Streamlit with editable-install fallback (POSIX)
set -euo pipefail
PROJECT_ROOT="$(pwd)"
VENV_PY="$PROJECT_ROOT/.venv/bin/python"

echo "Checking that 'src' package is importable in the virtualenv..."
if ! "$VENV_PY" -c "import importlib; importlib.import_module('src')" 2>/dev/null; then
	echo "'src' not importable — installing editable package (pip install -e .)"
	"$VENV_PY" -m pip install -e "$PROJECT_ROOT"
else
	echo "'src' is importable."
fi

echo "Launching Streamlit from project root..."
export PYTHONPATH="$PROJECT_ROOT"
"$VENV_PY" -m streamlit run src/dashboard/app.py
