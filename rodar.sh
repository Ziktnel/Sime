#!/usr/bin/env sh
# Ohmnia - sobe backend (8000) e frontend (3000). Requer Python 3.11+ e Node 20+.
set -e
cd "$(dirname "$0")"
[ -d backend/.venv ] || { python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt; }
[ -d frontend/node_modules ] || (cd frontend && npm install)
(cd backend && .venv/bin/uvicorn app.main:app --port 8000) &
(cd frontend && npm run dev)
