#!/usr/bin/env bash
# One-command start: creates venv, installs deps, loads .env, runs the server.
set -e
cd "$(dirname "$0")"
[ -f .env ] || cp .env.example .env
cd backend
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q -r requirements.txt
echo "Zevon running at http://localhost:8000  (make sure Ollama is running)"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
