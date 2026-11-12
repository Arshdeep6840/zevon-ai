# Zevon AI
**Your AI. Your Rules.**

Zevon is a self-hosted, local-first personal AI assistant: Ollama + FastAPI + a permission-controlled tool layer, with an installable app you can open from your phone over Tailscale.

| Name | What it is |
|---|---|
| **Zevon AI** | The product |
| **Zevon** | The assistant you talk to |
| **Zevon Core** | The architecture: agent engine, permission policy, memory, tool registry (`backend/app/core`) |
| **Zevon Mobile** | The installable phone/desktop app (PWA in `frontend/`) |
| **Zevon Extensions** | The plugin ecosystem: connectors in `backend/app/integrations` and `plugins/` |

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
ollama pull qwen3:8b       # pick a model that fits your RAM/VRAM; keep Ollama running
cd openzevon
./run.sh                   # Windows: run.bat  (creates .env + venv, installs deps, starts server)
```
Edit `.env` (created on first run): set `ZEVON_ALLOWED_FOLDERS` to folders Zevon may touch and `ZEVON_API_TOKEN` to a long random string, then restart. Open http://localhost:8000.

Try: "List files in <authorized folder>", "Plan how to organize my Downloads", then "Apply it" and approve in the Approvals tab.
Tests (no Ollama needed): `cd backend && pytest`.

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
`backend/app/core` (Zevon Core: llm, agent_engine, permissions, memory, tools) · `integrations/` (Zevon Extensions: google, system) · `scheduler/` · `frontend/` (Zevon Mobile) · `plugins/` · `docs/`

## Roadmap
1. Voice: faster-whisper STT + Piper TTS  2. YouTube/Calendar/Drive connectors  3. Playwright browser tool  4. ChromaDB memory  5. Conditional triggers (Gmail polling)  6. MCP client  7. React/Vite UI, Tauri desktop  8. Encrypt tokens at rest

Security notes: see SECURITY.md. License: Apache-2.0.
