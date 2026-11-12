@echo off
cd /d %~dp0
if not exist .env copy .env.example .env
cd backend
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
pip install -q -r requirements.txt
echo Jarvis running at http://localhost:8000  (make sure Ollama is running)
uvicorn app.main:app --host 0.0.0.0 --port 8000
