# Contributing to Zevon AI
Zevon Extensions are connectors that plug into Zevon Core.
Add an extension: create `backend/app/integrations/<group>/<name>.py`, register tools with `@registry.tool(name, description, json_schema, risk=...)`, import it in `integrations/__init__.py`.
Risk levels: `read`, `safe_write` (auto), `sensitive` (needs approval), `blocked` (denied). When unsure, pick `sensitive`.
Add a new LLM backend by subclassing `LLMProvider` in `core/llm.py`. Run tests: `cd backend && pytest`.
