#!/usr/bin/env bash
# Local launcher: builds frontend if missing, then starts FastAPI on 127.0.0.1:8000.
set -e
cd "$(dirname "$0")"

if [ ! -d "frontend/dist" ]; then
    echo "Building frontend (one-time)..."
    (cd frontend && [ -d node_modules ] || npm install && npm run build)
fi

if [ -f "venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    . venv/bin/activate
fi

python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
