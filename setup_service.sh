#!/usr/bin/env bash
# Helper script to install the automated 12-hour background sync service on Linux / macOS
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_CMD="python3"

if ! command -v "$PYTHON_CMD" &> /dev/null; then
    echo "[Error] python3 is not installed or not in PATH."
    exit 1
fi

"$PYTHON_CMD" "$SCRIPT_DIR/main.py" --install-service
