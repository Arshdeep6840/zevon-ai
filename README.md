# Zevon: Open-Source Personal AI Assistant

> **Local-first • Voice-enabled • Model-agnostic • Zero mandatory paid APIs**

Zevon is an extensible, privacy-preserving personal AI assistant designed to run completely on your own machine or inside your organization's private infrastructure. Built on open standards, Zevon combines local open-weight language models, speech recognition, speech synthesis, local memory, and a native **Model Context Protocol (MCP)** and **Agent Calling API** architecture.

---

## Key Features

- 🔒 **Local-First & Offline Capable:** Runs open-weight models via Ollama, `llama.cpp`, or `vLLM` with zero ambient audio upload and local SQLite persistence.
- 🔌 **Native MCP Host & Server:** Connects to any Model Context Protocol (MCP) server (filesystems, databases, browsers, developer tools) and exposes Zevon capabilities to external IDEs (Antigravity, Cursor, VS Code).
- 🤖 **Agent Calling Architecture:** Hierarchical sub-agent delegation for specialized workflows (coding, research, document synthesis).
- 🎙️ **Voice Assistant (Phase 2):** Configurable wake word ("Hey Zevon"), local VAD, faster-whisper speech-to-text, and local Piper/Kokoro TTS.
- 🖥️ **Cross-Platform Desktop & Web:** Tauri 2 desktop shell and responsive FastAPI web client.

---

## Repository Structure

```text
zevon/
├── apps/
│   └── desktop/            # Tauri 2 + React + TypeScript desktop client
├── services/
│   ├── api/                # FastAPI application, streaming endpoints, WebSocket
│   ├── assistant/          # Core agent orchestrator & state machine
│   ├── mcp_broker/         # MCP Host manager & tool registry
│   ├── mcp_server/         # Zevon's exposed MCP server endpoint
│   ├── model_gateway/      # Model registry & provider adapters (Ollama, Offline Mock)
│   ├── memory/             # Local SQLite conversation storage & sessions
│   ├── tool_runtime/       # Policy broker and sandboxing
│   └── voice/              # Voice pipeline stubs & interfaces
├── packages/
│   ├── agent-protocol/     # Typed inter-agent schemas and event contracts
│   ├── mcp-sdk/            # MCP client helpers and tool decorators
│   └── shared-schemas/     # Pydantic data contracts (Messages, ModelCard, Tasks)
├── tests/
│   └── unit/               # Backend and gateway unit tests
├── infra/
│   └── docker/             # Docker Compose for self-hosted deployments
├── docs/                   # Architectural specifications and ADRs
└── SRS.md                  # Software Requirements Specification (v1.0)
```

---

## Quickstart (Phase 1)

### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.ai) (optional for local LLM inference; an offline mock provider is included for testing)

### 1. Install Dependencies
```bash
# Using uv (recommended)
uv venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Or using standard pip
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Start the Backend API & Web Interface
```bash
python -m services.api.main
```
The server will start at `http://127.0.0.1:8000`. You can visit:
- **Interactive Chat Interface:** `http://127.0.0.1:8000/`
- **Swagger API Documentation:** `http://127.0.0.1:8000/docs`
- **Health Check:** `http://127.0.0.1:8000/api/v1/health`

### 3. Run Unit Tests
```bash
pytest
```

---

## License

Apache-2.0. See [LICENSE](LICENSE) for details.
