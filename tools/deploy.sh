#!/usr/bin/env bash
# Synchronisiert den Arbeitsstand vom Entwicklungsrechner auf den Pi (ohne Git).
# Der Pi braucht dafür keinen Schreibzugriff auf das Repository.
#
#   tools/deploy.sh [ferrari@ferrari.local]
set -euo pipefail

TARGET="${1:-ferrari@ferrari.local}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

rsync -az --delete \
    --exclude .git/ --exclude .venv/ --exclude __pycache__/ --exclude .pytest_cache/ \
    "$REPO/" "$TARGET:ferrari/"
ssh "$TARGET" 'cd ~/ferrari && .venv/bin/pip install -q -r requirements.txt'
