#!/usr/bin/env bash
# Mac / Linux: ./run.sh   (first time it sets everything up)
set -e
cd "$(dirname "$0")"
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }
[ -f .env ] || cp .env.example .env
echo "Kiosk: http://localhost:8000/kiosk   Officer: http://localhost:8000/officer"
exec .venv/bin/python -m uvicorn hv.server:app --host 0.0.0.0 --port 8000
