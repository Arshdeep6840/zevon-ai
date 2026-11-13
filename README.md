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
- **Models:** Ollama (local) by default; also llama.cpp / vLLM / LM Studio / OpenAI-compatible and Anthropic. Streaming replies. The UI says whether the model is local or cloud.
- **Agent:** tool calling, optional **planning step** for multi-part requests, rolling **conversation summaries**, repeated-call guard
- **Safety:** permission engine, approval queue, audit log, kill switch, untrusted-data marking, and a **Permissions screen** to set each tool to run automatically / ask me / never
- **Chat:** streaming, multiple conversations, plan display, spoken replies, push-to-talk and **hands-free mode with a "Hey Zevon" wake word** (local Whisper)
- **Memory:** SQLite history + ChromaDB semantic memory, with a **Memory screen** to view, edit and delete
- **Rules:** permanent rules, cron tasks, and **conditional rules** for new email, **calendar events, new files, Slack messages and time conditions**; enable/disable toggle
- **Google:** Gmail (read, draft, send, **labels, archive, mark read, trash**), YouTube (+transcripts), Calendar, Drive (read + **create Docs**), Tasks
- **Third-party:** Notion, Todoist (incl. **complete task**), Slack
- **Browser:** read pages (SSRF-safe), **screenshots, and click/fill/press with approval** (Playwright); **terminal** allowlist plus optional **ask-me-first mode** for other commands
- Sandboxed file tools, **MCP client**, **plugin system** (`docs/plugin-guide.md`)
- **Notifications:** in-app inbox, Web Push, **Android push (Firebase)**, desktop notifications
- React + Vite UI; Android project (Capacitor) and Tauri desktop scaffold with real app icons; `scripts/install_service.py` runs Zevon in the background at login/boot

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

## Code map for AI assistants (Graphify)
The repo ships a knowledge graph of its own code so an AI doesn't need to read every file for a small change:
`graphify-out/graph.html` (visual, open in a browser) · `GRAPH_REPORT.md` (summary) · `graph.json` (queryable) · `docs/CODEMAP.md` (hand-written map and recipes) · `CLAUDE.md` / `AGENTS.md` (assistant instructions).
Setup once: `./scripts/setup_graphify.sh`. Then `graphify query "where are approvals executed"`. After code changes: `graphify update .`.

## Status
Automated tests: 60 backend (`cd backend && pytest`) and 5 frontend (`cd frontend && npm test`), covering streaming, all three model providers (mocked HTTP), sessions/summaries, planning, per-tool policies, every trigger, Gmail labels, MCP over a real stdio server, ChromaDB, VAPID keys, FCM (mocked) and the service installer.
**Not yet verified by the author:** a live Ollama/llama.cpp/vLLM/Claude model, real Google/Notion/Todoist/Slack accounts, Playwright (browser interact/screenshot), faster-whisper/Piper audio and the hands-free loop on a real microphone, Web Push and Firebase push on a real device, the UI in a real browser, and the Android/Tauri builds (projects are generated, not compiled). Not solved: Zevon needs a machine that is on (see `docs/deployment.md`, Always-on).

Run tests: `cd backend && pytest`. License: Apache-2.0.
