# OpenJarvis AI

Self-hosted, local-first personal AI assistant: Ollama + FastAPI + a permission-controlled tool layer, with a installable PWA you can open from your phone over Tailscale. (Rename freely; there is an unrelated existing project called OpenJarvis.)

## What works in v0.1 (Phases 1, 2, 5 and part of 3/4)
- Chat with a local LLM via Ollama, with tool calling and conversation history
- Agent loop with tool registry, **permission engine**, **approval queue**, **audit log**, **kill switch**
- Long-term memory (SQLite) and custom instructions: permanent rules, scheduled (cron) tasks
- Sandboxed file tools: list/read, find duplicates, preview + apply folder organization, delete (approval required)
- Gmail connector: search, read, create draft (auto), send (approval required)
- PWA frontend: chat, approvals, audit log, tools, kill switch
- Tests that run without Ollama (`cd backend && pytest`)

Not built yet (see roadmap): voice (faster-whisper/Piper), YouTube/Calendar/Drive, browser automation, vector memory, conditional triggers, React rewrite, MCP.

## Quick start
```bash
# 1. Ollama
ollama pull qwen3:8b            # pick a model that fits your RAM/VRAM

# 2. Backend
cp .env.example .env            # edit JARVIS_ALLOWED_FOLDERS, JARVIS_API_TOKEN
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
set -a; source ../.env; set +a
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 3. Open http://localhost:8000
```
Try: "List files in /path/you/authorized", "Plan how to organize my Downloads", then "Apply it" and approve in the Approvals tab.

### Gmail
Create an OAuth client (Desktop app) in Google Cloud Console, enable the Gmail API, save it as `data/credentials.json`, then `pip install -r backend/requirements-google.txt && python scripts/google_auth.py`. Restart the backend. Use your own account in testing mode; public distribution triggers Google's restricted-scope verification.

### Phone access
Install Tailscale on PC and phone, open `http://<pc-tailscale-name>:8000` on the phone, and "Add to Home Screen". Your PC must be on.

### Scheduled instructions
```bash
curl -X POST localhost:8000/api/instructions -H 'Content-Type: application/json' \
  -d '{"name":"Morning briefing","kind":"scheduled","schedule":"0 8 * * *","text":"Summarize my unread emails."}'
```
Results are stored in the `scheduled-<id>` chat session. (Send `Authorization: Bearer <token>` if you set a token.)

## Layout
`backend/app/core` (llm, agent_engine, permissions, memory, tools) · `integrations/` (google, system) · `scheduler/` · `frontend/` · `plugins/` · `docs/`

## Roadmap
1. Voice: faster-whisper STT + Piper TTS  2. YouTube/Calendar/Drive connectors  3. Playwright browser tool  4. ChromaDB memory  5. Conditional triggers (Gmail polling)  6. MCP client  7. React/Vite UI, Tauri desktop  8. Encrypt tokens at rest

Security notes: see SECURITY.md. License: Apache-2.0.
