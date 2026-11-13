# Zevon Core architecture
```
Zevon Mobile (PWA / Android) · Zevon Desktop (Tauri) · voice
                 │  HTTPS / Tailscale, bearer token
        FastAPI  (backend/app/main.py)
                 │
   ┌─────────────┴──────────────┐
   Agent engine  ── Permission policy ── Approval queue ── Audit log
   (core/agent_engine.py)  (core/permissions.py)
   │        │
   LLM provider   Tool registry ── Zevon Extensions (google, productivity, system, tools, plugins/, MCP)
   (Ollama)       (core/tools.py)
   │
   Memory: SQLite (history, instructions, approvals, audit, notifications) + ChromaDB (semantic)
   Scheduler: cron instructions + Gmail email trigger → Notifier (in-app + Web Push)
```
**Rule 1:** the LLM never acts. It *requests* a registered tool; the policy returns allow / approve / deny by the tool's risk level.
**Rule 2:** everything a tool returns (emails, web pages, files, MCP output) is wrapped in `<untrusted_data>` and treated as data.

| Risk | Default | Examples |
|---|---|---|
| read | run | search email, read file, list calendar, browser read, terminal allowlist |
| safe_write | run | create draft, create task, save memory |
| sensitive | **needs approval** | send email, create calendar event, post to Slack, delete/move files, unknown MCP tools |
| blocked | denied | (reserved) |

Instruction kinds: *permanent* (injected into the system prompt), *scheduled* (cron), *conditional* (trigger `email:new`).
