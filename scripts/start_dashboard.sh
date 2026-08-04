#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VENV_PATH="${VENV_PATH:-.venv}"
HOST="${1:-127.0.0.1}"
PORT="${2:-8765}"

if [[ ! -d "$VENV_PATH" ]]; then
  echo "[start] missing $VENV_PATH. Run: ./scripts/setup_local.sh"
  exit 1
fi

# shellcheck source=/dev/null
source "$VENV_PATH/bin/activate"

python -m easy_apply serve --host "$HOST" --port "$PORT"
