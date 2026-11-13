# Zevon AI
**Your AI. Your Rules.**

Zevon is a self-hosted, local-first personal AI assistant: Ollama + FastAPI + a permission-controlled tool layer, usable from your PC, phone and desktop.

| Name | What it is |
|---|---|
| **Zevon AI** | The product |
| **Zevon** | The assistant you talk to |
| **Zevon Core** | The architecture: agent engine, permissions, memory, tool registry (`backend/app/core`) |
| **Zevon Mobile** | The React app: PWA, Android (Capacitor) and desktop (Tauri) from one codebase (`frontend/`) |
| **Zevon Extensions** | Connectors and plugins (`backend/app/integrations`, `plugins/`, MCP servers) |

## Features
- Local LLM chat with tool calling (Ollama); swappable provider interface
- **Permission engine, approval queue, audit log, kill switch**; untrusted-data marking against prompt injection
- Memory: SQLite history + **ChromaDB semantic memory** (Ollama embeddings, local)
- Instructions: permanent rules, **cron-scheduled tasks**, **conditional rules** ("when an important email arrives…")
- **Voice**: faster-whisper speech-to-text, Piper text-to-speech (browser speech fallback)
- **Google**: Gmail, YouTube (incl. transcripts), Calendar, Drive, Tasks
- **Third-party**: Notion, Todoist (API v1), Slack
- **Browser** page reading (Playwright optional, SSRF-protected) and a **restricted terminal**
- Sandboxed file tools (organize, duplicates, delete with approval)
- **MCP client** and a **plugin system** (`docs/plugin-guide.md`)
- **Notifications**: in-app inbox + Web Push
- React + Vite UI; Android project (Capacitor); Tauri desktop scaffold

## Quick start
```bash
ollama pull qwen3:8b
./run.sh            # Windows: run.bat  (creates .env + venv, installs deps, starts server)
```
Edit `.env` (set `ZEVON_ALLOWED_FOLDERS`, `ZEVON_API_TOKEN`), restart, open http://localhost:8000.
The built UI is in `frontend/dist`. To develop it: `cd frontend && npm install && npm run dev` (proxies to :8000).

Optional features (install what you want):
```bash
pip install -r backend/requirements-google.txt   # then: python scripts/google_auth.py
pip install -r backend/requirements-voice.txt
pip install -r backend/requirements-extras.txt   # chromadb, mcp, pywebpush, playwright (then: playwright install chromium)
ollama pull nomic-embed-text                      # for semantic memory
```
Google setup: create an OAuth client (Desktop app), enable Gmail, YouTube Data, Calendar, Drive and Tasks APIs, save as `data/credentials.json`, run the auth script, restart. Use your own account in testing mode.

Try: "List files in <folder>", "Organize my Downloads" (then approve), "What's on my calendar this week?", "Remember that I prefer short answers".
Rules tab example: *When a new email arrives* → "If it is from my boss, summarize it and say what I should reply."

More: `docs/architecture.md` · `docs/plugin-guide.md` · `docs/deployment.md` (Tailscale HTTPS, Android, Tauri, voice, push) · `docs/api.md` · `SECURITY.md`

## Status
Backend: 34 automated tests (real MCP server, ChromaDB, VAPID keys included). Not yet verified by the author: a live Ollama model, real Google/Notion/Todoist/Slack accounts, Playwright, faster-whisper/Piper audio, Web Push to a real device, the UI in a real browser, and the Android/Tauri builds (projects are generated, not compiled).

Run tests: `cd backend && pytest`. License: Apache-2.0.
