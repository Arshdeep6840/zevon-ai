# Graph Report - zevon-ai  (2026-11-13)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 737 nodes · 1622 edges · 38 communities (23 shown, 15 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 98 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `09c9feb5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Zevon Core: agent engine, permissions, tool registry
- Extensions: plugins, FCM push, Notion/Slack/Todoist
- API server: create_app() and all endpoints
- SQLite store, scheduler, notifier
- Triggers (base, calendar, Slack) + Google auth/calendar
- React app: API client, streaming, voice logic
- Tests: v3 endpoints, file/memory/stream
- Frontend package.json & Vite config
- Vector memory (ChromaDB)
- Config, filesystem sandbox, voice (Whisper/Piper)
- setup_graphify.sh
- Docker Compose
- Tauri desktop config
- Gmail connector (labels, archive, send)
- API models, browser tool, MCP client
- CI workflow
- PWA manifest
- Tauri capabilities
- run.sh
- push_to_github.sh
- Tests: core agent, approvals, sandbox
- LLM: base interface + Anthropic provider
- Cargo.toml
- LLM: OpenAI-compatible provider (llama.cpp, vLLM, cloud)
- LLM: Ollama provider
- Time trigger
- Icon generator script
- Voice & capabilities endpoints
- Test helper: fake HTTP stream
- LLM: ThinkFilter (streaming)
- Trigger validation
- Chat streaming endpoint

## God Nodes (most connected - your core abstractions)
1. `create_app()` - 66 edges
2. `Store` - 62 edges
3. `api()` - 35 edges
4. `AgentEngine` - 26 edges
5. `LLMResponse` - 25 edges
6. `ToolRegistry` - 23 edges
7. `LLMProvider` - 19 edges
8. `ToolCall` - 17 edges
9. `App()` - 17 edges
10. `Settings()` - 17 edges

## Surprising Connections (you probably didn't know these)
- `AgentEngine` --uses--> `LLMProvider`  [INFERRED]
  backend/app/core/agent_engine.py → backend/app/core/llm.py
- `test_vector_memory_semantic_recall()` --uses--> `ToolRegistry`  [INFERRED]
  backend/tests/test_v2.py → backend/app/core/tools.py
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

## Communities (38 total, 15 thin omitted)

### Community 0 - "Zevon Core: agent engine, permissions, tool registry"
Cohesion: 0.08
Nodes (16): AgentEngine, LLMResponse, register_memory_tools(), Decision, PermissionPolicy, Tool, ToolRegistry, deco() (+8 more)

### Community 1 - "Extensions: plugins, FCM push, Notion/Slack/Todoist"
Cohesion: 0.07
Nodes (33): _access_token(), send_fcm(), load_all(), load_plugins(), create_page(), _h(), register(), search() (+25 more)

### Community 3 - "SQLite store, scheduler, notifier"
Cohesion: 0.05
Nodes (11): Store, Notifier, ZevonScheduler, EmailTrigger, test_scheduler_registers_cron_jobs_and_runs(), FakeEngine, test_email_trigger_flow(), test_plugin_loader_survives_broken_plugin() (+3 more)

### Community 4 - "Triggers (base, calendar, Slack) + Google auth/calendar"
Cohesion: 0.05
Nodes (30): configured(), obj(), opt(), service(), create_event(), list_events(), register(), upcoming_keys() (+22 more)

### Community 5 - "React app: API client, streaming, voice logic"
Cohesion: 0.07
Nodes (55): api(), getServer(), getToken(), isNative(), setServer(), setToken(), streamChat(), urlB64ToUint8() (+47 more)

### Community 6 - "Tests: v3 endpoints, file/memory/stream"
Cohesion: 0.17
Nodes (11): Settings, FileTrigger, client(), sse(), test_capabilities_report_provider(), test_chat_stream_endpoint(), test_file_trigger_baseline_then_fires(), test_memories_crud_updates_vector() (+3 more)

### Community 7 - "Frontend package.json & Vite config"
Cohesion: 0.07
Nodes (35): dependencies, @capacitor/android@^8.6.0, @capacitor/core@^8.6.0, @capacitor/push-notifications@^8.1.3, react@^19.3.1, react-dom@^19.3.1, @tauri-apps/plugin-notification@^2.8.1, devDependencies (+27 more)

### Community 9 - "Config, filesystem sandbox, voice (Whisper/Piper)"
Cohesion: 0.08
Nodes (21): E(), L(), _load_dotenv(), synthesize(), apply_organize(), _category(), delete_file(), find_duplicates() (+13 more)

### Community 11 - "Docker Compose"
Cohesion: 0.11
Nodes (17): OLLAMA_HOST, ZEVON_API_TOKEN, ZEVON_DB, ZEVON_MODEL, image, volumes, services, ollama (+9 more)

### Community 12 - "Tauri desktop config"
Cohesion: 0.11
Nodes (17): app, security, windows, build, beforeBuildCommand, beforeDevCommand, devUrl, frontendDist (+9 more)

### Community 13 - "Gmail connector (labels, archive, send)"
Cohesion: 0.21
Nodes (18): archive_email(), _body(), create_draft(), create_label(), _header(), _label_ids(), list_labels(), list_message_ids() (+10 more)

### Community 14 - "API models, browser tool, MCP client"
Cohesion: 0.05
Nodes (30): _attr(), _call_tool(), _list_tools(), _params(), register_mcp(), func(), _run_sync(), check_url() (+22 more)

### Community 15 - "CI workflow"
Cohesion: 0.16
Nodes (14): runs-on, steps, runs-on, steps, jobs, backend, frontend, name (+6 more)

### Community 16 - "PWA manifest"
Cohesion: 0.22
Nodes (8): background_color, description, display, icons, name, short_name, start_url, theme_color

### Community 17 - "Tauri capabilities"
Cohesion: 0.33
Nodes (5): description, identifier, permissions, $schema, windows

### Community 23 - "Tests: core agent, approvals, sandbox"
Cohesion: 0.24
Nodes (9): ToolCall, FakeLLM, make(), sandbox(), test_delete_requires_approval_then_runs(), test_kill_switch_stops_agent(), test_organize_preview_and_apply(), test_read_tool_runs_automatically() (+1 more)

### Community 26 - "LLM: base interface + Anthropic provider"
Cohesion: 0.22
Nodes (4): AnthropicProvider, LLMProvider, make_provider(), test_anthropic_convert_and_parse()

### Community 29 - "LLM: OpenAI-compatible provider (llama.cpp, vLLM, cloud)"
Cohesion: 0.33
Nodes (4): _args(), _is_local_url(), OpenAICompatProvider, test_openai_compat_convert_chat_and_stream()

### Community 30 - "LLM: Ollama provider"
Cohesion: 0.24
Nodes (6): OllamaProvider, _strip_think(), _resp(), test_ollama_down_gives_friendly_error(), test_ollama_provider_parses_tool_calls_and_strips_think(), fake_post()

### Community 31 - "Time trigger"
Cohesion: 0.31
Nodes (3): TimeTrigger, FakeEngine, test_time_trigger_interval_and_window()

### Community 32 - "Icon generator script"
Cohesion: 0.32
Nodes (3): art(), main(), save()

### Community 33 - "Voice & capabilities endpoints"
Cohesion: 0.29
Nodes (7): stt_available(), tts_available(), capabilities(), features(), health(), speak(), transcribe()

### Community 36 - "Trigger validation"
Cohesion: 0.67
Nodes (3): add_instruction(), valid_trigger(), test_valid_triggers()

## Knowledge Gaps
- **1 isolated node(s):** `zevon-desktop`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 234 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `create_app()` connect `API server: create_app() and all endpoints` to `Zevon Core: agent engine, permissions, tool registry`, `Extensions: plugins, FCM push, Notion/Slack/Todoist`, `Voice & capabilities endpoints`, `SQLite store, scheduler, notifier`, `Trigger validation`, `Triggers (base, calendar, Slack) + Google auth/calendar`, `Tests: v3 endpoints, file/memory/stream`, `Chat streaming endpoint`, `Vector memory (ChromaDB)`, `API models, browser tool, MCP client`, `Tests: core agent, approvals, sandbox`, `LLM: base interface + Anthropic provider`, `Time trigger`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `create_app()` (e.g. with `Settings` and `LLMProvider`) actually correct?**
  _`create_app()` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `zevon-desktop` to the rest of the system?**
  _1 weakly-connected nodes found - possible missing edges._
- **Should `Zevon Core: agent engine, permissions, tool registry` be split into smaller, more focused modules?**
  _Cohesion score 0.07756813417190776 - nodes in this community are weakly interconnected._
- **Why does `Store` connect `SQLite store, scheduler, notifier` to `Zevon Core: agent engine, permissions, tool registry`, `Extensions: plugins, FCM push, Notion/Slack/Todoist`, `API server: create_app() and all endpoints`, `Triggers (base, calendar, Slack) + Google auth/calendar`, `Tests: v3 endpoints, file/memory/stream`, `API models, browser tool, MCP client`, `Time trigger`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Store` (e.g. with `test_mcp_server_tools_registered_and_gated()` and `test_vector_memory_semantic_recall()`) actually correct?**
  _`Store` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `Extensions: plugins, FCM push, Notion/Slack/Todoist` be split into smaller, more focused modules?**
  _Cohesion score 0.06578947368421052 - nodes in this community are weakly interconnected._