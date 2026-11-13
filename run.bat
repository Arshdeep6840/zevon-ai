@echo off
cd /d %~dp0
if not exist .env copy .env.example .env
if not exist frontend\dist (where npm >nul 2>nul && (pushd frontend & call npm install --no-audit --no-fund & call npm run build & popd))
cd backend
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
pip install -q -r requirements.txt
echo Zevon running at http://localhost:8000  (make sure Ollama is running)
uvicorn app.main:app --host 0.0.0.0 --port 8000
