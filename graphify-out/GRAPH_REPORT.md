# Graph Report - zevon-ai  (2026-11-13)

## Corpus Check
- 67 files · ~12,738 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: (none) 6, .example 1, .css 1)

## Summary
- 505 nodes · 1017 edges · 29 communities (17 shown, 12 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 64 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0bb2a9e4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Zevon Core: agent engine, LLM providers, permissions
- Tool registry, voice, memory tools (+v2 tests)
- API server (main.py), notifications, email trigger
- SQLite store & scheduler
- Google connectors: YouTube, Calendar, Drive, Tasks, auth
- React app (Zevon Mobile): components & api.js
- Config + Notion/Todoist/Slack connectors
- Frontend package.json & Vite config
- Vector memory (ChromaDB)
- Sandboxed filesystem & restricted terminal
- setup_graphify.sh
- Docker Compose
- Tauri desktop config
- Gmail connector
- Browser tool (SSRF-safe)
- CI workflow
- PWA manifest
- Tauri capabilities
- run.sh
- push_to_github.sh
- Cargo.toml

## God Nodes (most connected - your core abstractions)
1. `create_app()` - 43 edges
2. `Store` - 39 edges
3. `api()` - 25 edges
4. `ToolRegistry` - 19 edges
5. `AgentEngine` - 16 edges
6. `LLMProvider` - 14 edges
7. `ZevonScheduler` - 13 edges
8. `App()` - 13 edges
9. `safe_path()` - 12 edges
10. `Settings()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `create_app()` --uses--> `Settings`  [INFERRED]
  backend/app/main.py → backend/app/config.py
- `AgentEngine` --uses--> `ToolRegistry`  [INFERRED]
  backend/app/core/agent_engine.py → backend/app/core/tools.py
- `create_app()` --uses--> `LLMProvider`  [INFERRED]
  backend/app/main.py → backend/app/core/llm.py
- `test_mcp_server_tools_registered_and_gated()` --uses--> `Store`  [INFERRED]
  backend/tests/test_v2.py → backend/app/core/memory.py
- `test_vector_memory_semantic_recall()` --uses--> `Store`  [INFERRED]
  backend/tests/test_v2.py → backend/app/core/memory.py

## Import Cycles
- 2-file cycle: `backend/app/integrations/google/__init__.py -> backend/app/integrations/google/youtube.py -> backend/app/integrations/google/__init__.py`
- 2-file cycle: `backend/app/integrations/google/__init__.py -> backend/app/integrations/google/drive.py -> backend/app/integrations/google/__init__.py`
- 2-file cycle: `backend/app/integrations/google/__init__.py -> backend/app/integrations/google/gmail.py -> backend/app/integrations/google/__init__.py`
- 2-file cycle: `backend/app/integrations/google/__init__.py -> backend/app/integrations/google/calendar.py -> backend/app/integrations/google/__init__.py`
- 2-file cycle: `backend/app/integrations/google/__init__.py -> backend/app/integrations/google/tasks.py -> backend/app/integrations/google/__init__.py`

## Communities (29 total, 12 thin omitted)

### Community 0 - "Zevon Core: agent engine, LLM providers, permissions"
Cohesion: 0.07
Nodes (21): Settings, AgentEngine, LLMProvider, LLMResponse, make_provider(), OllamaProvider, ToolCall, Decision (+13 more)

### Community 1 - "Tool registry, voice, memory tools (+v2 tests)"
Cohesion: 0.08
Nodes (21): register_memory_tools(), Tool, ToolRegistry, deco(), load_plugins(), client(), fake_embed(), FakeLLM (+13 more)

### Community 2 - "API server (main.py), notifications, email trigger"
Cohesion: 0.07
Nodes (15): stt_available(), tts_available(), configured(), register_all(), create_app(), auth(), capabilities(), features() (+7 more)

### Community 3 - "SQLite store & scheduler"
Cohesion: 0.09
Nodes (6): Store, ZevonScheduler, test_permanent_instructions_and_memory_reach_system_prompt(), test_scheduler_registers_cron_jobs_and_runs(), test_plugin_loader_survives_broken_plugin(), test_scheduler_notifies()

### Community 4 - "Google connectors: YouTube, Calendar, Drive, Tasks, auth"
Cohesion: 0.10
Nodes (19): obj(), opt(), service(), create_event(), list_events(), register(), read_file(), register() (+11 more)

### Community 5 - "React app (Zevon Mobile): components & api.js"
Cohesion: 0.16
Nodes (28): api(), getServer(), getToken(), isNative(), setServer(), setToken(), urlB64ToUint8(), App() (+20 more)

### Community 6 - "Config + Notion/Todoist/Slack connectors"
Cohesion: 0.13
Nodes (18): E(), L(), _load_dotenv(), load_all(), create_page(), _h(), register(), search() (+10 more)

### Community 7 - "Frontend package.json & Vite config"
Cohesion: 0.08
Nodes (30): dependencies, @capacitor/android@^8.6.0, @capacitor/core@^8.6.0, react@^19.3.1, react-dom@^19.3.1, devDependencies, @capacitor/cli@^8.6.0, @tauri-apps/cli@^2.12.4 (+22 more)

### Community 8 - "Vector memory (ChromaDB)"
Cohesion: 0.08
Nodes (8): Notifier, OllamaEmbedder, VectorMemory, ChatIn, InstructionIn, KillIn, PushSub, SpeakIn

### Community 9 - "Sandboxed filesystem & restricted terminal"
Cohesion: 0.13
Nodes (12): synthesize(), apply_organize(), _category(), delete_file(), find_duplicates(), list_dir(), _plan(), plan_organize() (+4 more)

### Community 11 - "Docker Compose"
Cohesion: 0.11
Nodes (17): OLLAMA_HOST, ZEVON_API_TOKEN, ZEVON_DB, ZEVON_MODEL, image, volumes, services, ollama (+9 more)

### Community 12 - "Tauri desktop config"
Cohesion: 0.11
Nodes (17): app, security, windows, build, beforeBuildCommand, beforeDevCommand, devUrl, frontendDist (+9 more)

### Community 13 - "Gmail connector"
Cohesion: 0.33
Nodes (10): _body(), create_draft(), _header(), list_message_ids(), _raw(), read_email(), register(), search_emails() (+2 more)

### Community 14 - "Browser tool (SSRF-safe)"
Cohesion: 0.11
Nodes (16): _attr(), _call_tool(), _list_tools(), _params(), register_mcp(), func(), _run_sync(), check_url() (+8 more)

### Community 15 - "CI workflow"
Cohesion: 0.16
Nodes (14): runs-on, steps, runs-on, steps, jobs, backend, frontend, name (+6 more)

### Community 16 - "PWA manifest"
Cohesion: 0.22
Nodes (8): background_color, description, display, icons, name, short_name, start_url, theme_color

### Community 17 - "Tauri capabilities"
Cohesion: 0.33
Nodes (5): description, identifier, permissions, $schema, windows

## Knowledge Gaps
- **1 isolated node(s):** `zevon-desktop`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 170 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `create_app()` connect `API server (main.py), notifications, email trigger` to `Zevon Core: agent engine, LLM providers, permissions`, `Tool registry, voice, memory tools (+v2 tests)`, `SQLite store & scheduler`, `Config + Notion/Todoist/Slack connectors`, `Vector memory (ChromaDB)`, `Browser tool (SSRF-safe)`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `create_app()` (e.g. with `Settings` and `LLMProvider`) actually correct?**
  _`create_app()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `zevon-desktop` to the rest of the system?**
  _1 weakly-connected nodes found - possible missing edges._
- **Should `Zevon Core: agent engine, LLM providers, permissions` be split into smaller, more focused modules?**
  _Cohesion score 0.07077922077922078 - nodes in this community are weakly interconnected._
- **Why does `Store` connect `SQLite store & scheduler` to `Zevon Core: agent engine, LLM providers, permissions`, `Vector memory (ChromaDB)`, `API server (main.py), notifications, email trigger`, `Tool registry, voice, memory tools (+v2 tests)`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Store` (e.g. with `test_mcp_server_tools_registered_and_gated()` and `test_vector_memory_semantic_recall()`) actually correct?**
  _`Store` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `Tool registry, voice, memory tools (+v2 tests)` be split into smaller, more focused modules?**
  _Cohesion score 0.08414634146341464 - nodes in this community are weakly interconnected._