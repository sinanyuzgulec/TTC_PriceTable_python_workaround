#!/usr/bin/env bash
# Helper script to trigger an immediate PriceTable sync on Linux / macOS
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_CMD="python3"

if ! command -v "$PYTHON_CMD" &> /dev/null; then
    echo "[Error] python3 is not installed or not in PATH."
    exit 1
fi

"$PYTHON_CMD" "$SCRIPT_DIR/main.py" --sync
