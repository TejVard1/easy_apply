#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VENV_PATH="${VENV_PATH:-.venv}"
WITH_AUTOMATION="${1:-}"

if [[ ! -d "$VENV_PATH" ]]; then
  echo "[setup] creating virtual environment at $VENV_PATH"
  python3 -m venv "$VENV_PATH"
else
  echo "[setup] reusing existing virtual environment at $VENV_PATH"
fi

# shellcheck source=/dev/null
source "$VENV_PATH/bin/activate"

python -m pip install --upgrade pip setuptools wheel
python -m pip install --no-build-isolation -e .

if [[ "$WITH_AUTOMATION" == "--with-automation" ]]; then
  python -m pip install pypdf python-docx playwright
  python -m playwright install chromium
fi

echo "[setup] done"
