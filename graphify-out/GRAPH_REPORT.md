# Graph Report - zevon-ai  (2026-11-20)

## Corpus Check
- Corpus is ~15,800 words - fits in a single context window. You may not need a graph.

## Summary
- 408 nodes · 838 edges · 27 communities (13 shown, 14 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 114 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Chat Turn & SSE Streaming
- Model Provider Adapters & Gateway
- Frontend Chat Web UI
- Health & Model Hardware Routes
- Shared Pydantic Data Contracts
- Agent Calling Protocol & RPC
- GitHub Actions CI Pipeline
- Async SQLite Memory Database
- Desktop Shell Node Dependencies
- Tauri Desktop Configuration
- FastAPI Integration Test Suite
- API Dependency Injection Providers
- FastAPI Application Server Factory
- Web UI Components & Architecture
- Bidirectional Realtime WebSocket
- Zevon Product Architecture & SRS
- API Configuration & Environment
- Web UI Index Server Route
- Zevon Core Package Metadata
- Desktop Shell Package Metadata
- Phase 2 Voice Roadmap
- Phase 3 MCP Orchestration Roadmap

## God Nodes (most connected - your core abstractions)
1. `MemoryRepository` - 40 edges
2. `ModelRegistry` - 34 edges
3. `Message` - 27 edges
4. `ModelCard` - 22 edges
5. `Role` - 18 edges
6. `chat_turn()` - 16 edges
7. `BaseModelProvider` - 16 edges
8. `OfflineMockProvider` - 15 edges
9. `realtime_chat_socket()` - 12 edges
10. `init_db()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `realtime_chat_socket()` --uses--> `Role`  [INFERRED]
  services/api/routes/realtime.py → packages/shared_schemas/models.py
- `test_model_registry_offline_mode()` --uses--> `Role`  [INFERRED]
  tests/test_model_gateway.py → packages/shared_schemas/models.py
- `test_offline_mock_provider()` --uses--> `Role`  [INFERRED]
  tests/test_model_gateway.py → packages/shared_schemas/models.py
- `MemoryRepository` --uses--> `Message`  [INFERRED]
  services/memory/repository.py → packages/shared_schemas/models.py
- `ModelRegistry` --uses--> `Message`  [INFERRED]
  services/model_gateway/registry.py → packages/shared_schemas/models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Zevon User Personas** — srs_persona_everyday_user, srs_persona_developer, srs_persona_business, srs_persona_creator [EXTRACTED 1.00]
- **Extensibility Architecture Standards** — srs_product_principles, srs_mcp_protocol_standard, srs_agent_calling_api [EXTRACTED 1.00]

## Communities (27 total, 14 thin omitted)

### Community 0 - "Chat Turn & SSE Streaming"
Cohesion: 0.08
Nodes (19): Conversation, Role, chat_turn(), clear_all_conversations(), create_conversation(), CreateConversationRequest, delete_conversation(), export_conversation() (+11 more)

### Community 1 - "Model Provider Adapters & Gateway"
Cohesion: 0.09
Nodes (8): Message, ModelCard, BaseModelProvider, OfflineMockProvider, OllamaProvider, HardwareProfile, test_hardware_profiler(), test_offline_mock_provider()

### Community 2 - "Frontend Chat Web UI"
Cohesion: 0.08
Nodes (46): activeTitleEl, appendMessage(), chatMessagesEl, clearAllBtn, closeSettingsBtn, conversationListEl, conversationsData, createNewConversation() (+38 more)

### Community 3 - "Health & Model Hardware Routes"
Cohesion: 0.09
Nodes (13): health_check(), get_active_model(), get_hardware_profile(), list_models(), OfflineToggleRequest, SelectModelRequest, set_active_model(), toggle_offline_mode() (+5 more)

### Community 4 - "Shared Pydantic Data Contracts"
Cohesion: 0.11
Nodes (15): ApprovalRequest, ChatChunk, ChatRequest, RiskLevel, TaskPlanStep, TaskState, TaskStatus, utc_now() (+7 more)

### Community 5 - "Agent Calling Protocol & RPC"
Cohesion: 0.15
Nodes (9): AgentEvent, AgentEventType, AgentRPCRequest, AgentRPCResponse, AgentTaskRequest, AgentTaskResponse, ToolCallDefinition, ToolResultDefinition (+1 more)

### Community 6 - "GitHub Actions CI Pipeline"
Cohesion: 0.11
Nodes (18): jobs, test, python-version, name, on, pull_request, push, branches (+10 more)

### Community 7 - "Async SQLite Memory Database"
Cohesion: 0.18
Nodes (4): get_db(), init_db(), memory_repo(), temp_db_path()

### Community 8 - "Desktop Shell Node Dependencies"
Cohesion: 0.13
Nodes (17): dependencies, @tauri-apps/api@^2.0.0, @tauri-apps/plugin-shell@^2.0.0, description, devDependencies, @tauri-apps/cli@^2.0.0, name, private (+9 more)

### Community 9 - "Tauri Desktop Configuration"
Cohesion: 0.12
Nodes (16): app, security, windows, withGlobalTauri, build, devUrl, frontendDist, bundle (+8 more)

### Community 10 - "FastAPI Integration Test Suite"
Cohesion: 0.14
Nodes (3): client(), setup_test_database(), test_realtime_websocket()

### Community 13 - "Web UI Components & Architecture"
Cohesion: 0.18
Nodes (11): Zevon Repository Architecture Layout, Phase 1 Quickstart Instructions, System & Privacy Settings Modal, Conversation & Persona Sidebar, Zevon Web Chat UI Shell, Delivery Phase 1: Foundation & Local Chat, Hardware Profiles and Tiers, Persona: Business & Team (+3 more)

### Community 15 - "Zevon Product Architecture & SRS"
Cohesion: 0.29
Nodes (7): Zevon Project Readme Overview, Standardized Agent Calling API, Zevon Executive Summary and Product Vision, Functional Requirements Matrix, Model Context Protocol Standard, Core Product Principles, Task Risk Taxonomy (R0 - R3)

## Knowledge Gaps
- **14 isolated node(s):** `zevon-desktop`, `zevon`, `Persona: Developer & Engineer`, `Persona: Business & Team`, `Persona: Creator & Media` (+9 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 177 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MemoryRepository` connect `Chat Turn & SSE Streaming` to `Model Provider Adapters & Gateway`, `Health & Model Hardware Routes`, `Shared Pydantic Data Contracts`, `Async SQLite Memory Database`, `API Dependency Injection Providers`, `Bidirectional Realtime WebSocket`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `MemoryRepository` (e.g. with `chat_turn()` and `clear_all_conversations()`) actually correct?**
  _`MemoryRepository` has 14 INFERRED edges - model-reasoned connections that need verification._
- **What connects `zevon-desktop`, `zevon`, `Persona: Developer & Engineer` to the rest of the system?**
  _14 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Chat Turn & SSE Streaming` be split into smaller, more focused modules?**
  _Cohesion score 0.08490566037735849 - nodes in this community are weakly interconnected._
- **Why does `ModelRegistry` connect `Health & Model Hardware Routes` to `Chat Turn & SSE Streaming`, `Model Provider Adapters & Gateway`, `Shared Pydantic Data Contracts`, `Async SQLite Memory Database`, `API Dependency Injection Providers`, `Bidirectional Realtime WebSocket`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `ModelRegistry` (e.g. with `get_gateway()` and `chat_turn()`) actually correct?**
  _`ModelRegistry` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Should `Model Provider Adapters & Gateway` be split into smaller, more focused modules?**
  _Cohesion score 0.09042553191489362 - nodes in this community are weakly interconnected._