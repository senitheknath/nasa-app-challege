#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -x .venv/bin/python ]]; then
  python_bin=.venv/bin/python
elif [[ -x /home/asus/.venvs/agroshift-prep/bin/python ]]; then
  python_bin=/home/asus/.venvs/agroshift-prep/bin/python
else
  python_bin=python3
fi
# Automatically release port 8501 if an existing instance is already running
fuser -k 8501/tcp 2>/dev/null || true
sleep 0.5
exec "$python_bin" -m scripts.run_local --port 8501
