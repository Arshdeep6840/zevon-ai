ZEVON

Open-Source Personal AI Assistant

Software Requirements Specification (SRS)Product vision • System architecture • Technology stack • Delivery phases

Version 1.0  |  20 November 2026Prepared as a developer-ready foundation for an open-source project

Devepoler: Arshdeep Singh 
Email: Arshdeepsingh17092@gmail.com


Document control

Field

Value

Product

Zevon — local-first, voice-enabled personal AI assistant

Document

Software Requirements Specification (SRS)

Version / status

1.0 / Proposed baseline

Target audiences

Individual users, developers, businesses, teams and creators

Primary principle

No mandatory paid APIs, subscriptions or proprietary runtime dependencies

Deployment model

Local-first desktop; optional self-hosted server / private business deployment

Reference inspiration

OpenJarvis-style composable, local-first assistant architecture; Zevon is an independent product concept



Contents

1. Executive summary and product vision

2. Goals, non-goals and product principles

3. User personas and use cases

4. Functional requirements

5. Non-functional requirements

6. System architecture and data flow

7. Recommended open-source technology stack

8. AI model strategy and hardware profiles

9. Security, privacy and safety design

10. UX and interaction requirements

11. API and extensibility requirements

12. Testing and acceptance criteria

13. Delivery roadmap and phases

14. Risks, assumptions and constraints

15. Definition of done and launch checklist

16. References and license due diligence

1. Executive summary

Zevon is an extensible personal AI assistant that users can speak to through a configurable wake word (“Hey Zevon” / “Zevon”), chat with, and delegate multi-step work to. It should run on a user's own computer or on infrastructure controlled by their organization. It combines local open-weight language models, speech recognition, speech synthesis, memory, retrieval, tool integrations and a permissioned agent runtime.

The product is intended to serve three audiences through one core platform: everyday users who want a capable voice assistant; developers who want an extensible agent platform and SDK; and businesses/creators who need private workflows for documents, research, content production, operations and team knowledge.

The system must be model-agnostic. It should select a model appropriate to available hardware and task complexity rather than hard-code one model as “the best”. A compact model can handle routing and simple requests; a stronger reasoning/coding model can be selected for difficult work. All inference should be local by default. Optional remote inference is out of scope for the zero-paid baseline and must never be enabled silently.

Important feasibility boundary: “able to do any task” is not a testable or safe requirement. Zevon should support a broad, growing set of tasks through tools and plugins, explain unsupported requests, and ask for approval before consequential actions. It cannot guarantee success on every task, nor bypass operating-system permissions, website restrictions, hardware limits or human judgement.

2. Goals, non-goals and product principles

2.1 Product goals

Provide natural voice and text interaction with a configurable wake word and hands-free follow-up conversation.

Execute complex, multi-step tasks using planning, tools, memory, retries, checkpoints and user approvals.

Work offline for core assistant functions after models and dependencies are installed.

Support Windows, Linux and macOS desktop experiences, with a responsive web interface for self-hosted deployments.

Offer separate experiences and permission profiles for personal users, developers, businesses and creators.

Expose an MCP-native (Model Context Protocol) runtime and Agent Calling API architecture, alongside REST/WebSocket APIs, enabling zero-friction plug-and-play addition of new models, tools, features, and external agents.

Keep user data local or within an organization's infrastructure by default.

Allow operators to replace models, speech engines, databases and integrations without rewriting the product.

2.2 Non-goals for initial release

An unrestricted autonomous agent with permanent shell, filesystem, browser or payment access.

Guaranteed execution of every possible real-world task or guaranteed correctness of model output.

Replacing professional judgement in legal, medical, financial, security or other regulated domains.

Shipping a hosted SaaS service that requires paid inference APIs.

Building a new foundation model or training a frontier LLM from scratch.

Supporting every third-party app at launch; integrations will be added incrementally.

2.3 Product principles

Principle

Requirement

Local-first

Local inference and local storage are defaults; network use is visible and configurable.

Open-source-first

Prefer OSI-approved licenses for code and permissively licensed model weights where practical; maintain an SBOM.

Model-agnostic

Provider adapters isolate model-specific APIs and allow swapping inference engines.

Human-in-control

Preview, confirmation, undo/rollback and audit trail for risky or external actions.

Composable

Core, tools, agents, memory and interfaces are independently replaceable.

Protocol-first extensibility (MCP & Agent API)

Tools, contextual resources, and agent capabilities are decoupled from the core runtime via the Model Context Protocol (MCP) and standardized Agent Calling APIs, ensuring seamless plug-and-play addition of new models, tools, and features without orchestrator refactoring.

Accessible

Voice is optional; keyboard, screen-reader and text workflows remain first-class.

Honest capability

Show progress, uncertainty, permissions, failures and task completion evidence.



3. User personas and use cases

Persona

Primary needs

Example workflows

Everyday user

Simple, reliable assistant; reminders; files; desktop actions; voice-first use.

Ask questions, summarize PDFs, organize files, create reminders, dictate messages.

Developer

Code-aware agent, terminal in sandbox, Git, IDE and API access; extensibility.

Explain a repo, write tests, debug errors, create PR-ready changes, run local scripts.

Business / team

Private deployment, roles, auditability, shared knowledge and controlled integrations.

Search internal documents, draft reports, summarize meetings, prepare workflows.

Creator

Research, writing, ideation, media workflows and repeatable production pipelines.

Research topics, outline scripts, draft captions, transcribe audio, organize assets.



3.1 Representative user journeys

Voice: user says “Hey Zevon”, the wake-word detector activates, Zevon listens, transcribes, confirms intent if ambiguous, responds by voice and returns to a low-power listening state.

Complex task: “Review this project, find failing tests, fix the simple issues and explain the changes.” Zevon inspects the selected repository, proposes a plan, works in a sandbox, runs tests, presents a diff and asks before applying or committing changes.

Creator workflow: “Turn these notes and this transcript into a 5-minute video script.” Zevon retrieves the selected files, drafts a script, labels assumptions and saves a versioned output.

Business workflow: “Find the latest policy on travel reimbursement and draft a response.” Zevon searches authorized knowledge sources, cites source documents and drafts without sending automatically.

Developer extension: a developer builds a plugin with a typed manifest, permissions, input/output schema, tests and UI metadata, then installs it into a user-approved workspace.

4. Functional requirements

Priority legend: P0 = required for first usable release; P1 = important follow-on; P2 = later enhancement.

ID

Requirement

Priority

FR-001

Provide text chat with streaming responses, conversation history and cancellation.

P0

FR-002

Support a configurable wake phrase, initially “Hey Zevon” and “Zevon”; provide push-to-talk fallback.

P0

FR-003

Detect wake word locally; do not stream ambient audio to a server before activation.

P0

FR-004

Capture speech, apply voice activity detection, transcribe locally and display editable transcript.

P0

FR-005

Speak responses using locally hosted TTS; allow voice, speed, volume and mute settings.

P0

FR-006

Support barge-in: user can interrupt spoken output and issue a new command.

P1

FR-007

Maintain short-term conversation context and user-controlled long-term memory.

P0

FR-008

Plan multi-step tasks, track state, retry bounded failures and report final results.

P0

FR-009

Call tools and sub-agents through an MCP-native, permission-checked Tool & Agent Gateway with unified schema validation, parameter constraints, and audit logging.

P0

FR-010

Provide core tools: calculator, time/date, file search/read/write, notes, local app launch and web research adapter.

P0

FR-011

Provide a sandboxed code execution tool with resource/time limits and explicit workspace selection.

P1

FR-012

Provide browser automation through Playwright with domain allowlists and confirmation for submissions/purchases.

P1

FR-013

Support document ingestion, chunking, embeddings, retrieval and source citations (RAG).

P1

FR-014

Provide profiles: Personal, Developer, Business and Creator, each with templates and permission presets.

P0

FR-015

Provide MCP server and tool management: discovery, installation, activation/deactivation, version pinning, and scoped permission review.

P0

FR-016

Support native Model Context Protocol (MCP) Host/Client architecture over STDIO and SSE/HTTP, dynamically discovering and injecting tool/resource schemas into the active model's function calling context.

P0

FR-017

Allow user to inspect, edit, export and delete memory and conversation data.

P0

FR-018

Provide task timeline, plan preview, tool activity, approvals, output artifacts and audit events.

P0

FR-019

Support scheduled and recurring tasks only after user configures schedule and permissions.

P2

FR-020

Support organization mode with user roles, shared tools, policy controls and admin audit.

P2

FR-021

Allow switching model and inference engine from settings; expose model capability and hardware fit.

P0

FR-022

Provide offline status and clearly identify features requiring network access.

P0

FR-023

Provide multilingual speech/text support through selectable language models and speech packs.

P1

FR-024

Allow user to export data and configuration in documented portable formats.

P1

FR-025

Provide an Agent Calling API & Agent-to-Agent architecture enabling the main orchestrator to invoke, delegate subtasks to, and receive structured results from specialized sub-agents (e.g., Coder Agent, Web Research Agent, Document Specialist) with task checkpoints and isolated permission boundaries.

P0

FR-026

Provide dual-role MCP capability by exposing Zevon as an MCP Server (over SSE/STDIO), allowing external agent hosts, developer tools, and IDEs (e.g., Antigravity, Cursor, Claude Code, VS Code) to consume Zevon's internal tools, memory, and specialized agents.

P1



5. Non-functional requirements

Area

Requirement / target

Performance

Wake-word detection target: <250 ms local detection after phrase completion on supported hardware. Voice first-token response target: <3 s on reference hardware for compact models; measured and reported, not guaranteed.

Reliability

Core app should recover from model-server restart, tool timeout and network loss without corrupting task state.

Availability

Desktop core available whenever the user's machine is running; business self-hosted target defined by deployment SLA.

Privacy

No ambient audio upload; local storage by default; telemetry opt-in; redact secrets from logs.

Security

Least privilege, scoped tokens, sandboxing, signed plugin packages where possible, dependency scanning and audit logs.

Portability

Windows 11+, recent macOS and mainstream Linux distributions; architecture adapters isolate OS-specific actions.

Accessibility

Keyboard-only operation, captions/transcripts, adjustable text, screen-reader labels and push-to-talk.

Maintainability

Typed interfaces, modular packages, documented architecture decisions, automated tests and migration scripts.

Extensibility

New model provider, tool, voice, UI surface or workflow can be added without changing the orchestration core.

Localization

UTF-8 throughout; locale-aware dates, number formats, language selection and transcription settings.



6. System architecture and data flow

Recommended architecture: a modular monolith for the first release, split into independently deployable services only when scale or platform constraints justify it. This reduces early operational complexity while preserving clean interfaces.

Layer

Responsibilities

Main components

Client layer

Desktop tray/app, chat, mic state, task timeline, settings, approvals.

Tauri + React/TypeScript; optional web client.

Voice layer

Wake phrase, VAD, audio capture, ASR, TTS, interruption handling.

openWakeWord/custom model, Silero VAD, faster-whisper or whisper.cpp, Piper/Kokoro.

API & identity

Sessions, auth, WebSocket streaming, rate limits, tenant context.

FastAPI, Pydantic, OAuth2/OIDC; Keycloak for business SSO.

Orchestration

Multi-agent coordination, sub-agent delegation via Agent Calling API, intent routing, planning, state machine, retries, checkpoints.

LangGraph or PydanticAI; standardized Agent-to-Agent message protocol.

Model gateway

Model registry, task routing, inference adapters, quantization profiles, and universal MCP tool-call schema adapter.

Ollama for local dev; llama.cpp for GGUF/CPU; vLLM for GPU server.

MCP & Tool runtime (Host & Server)

MCP Host runtime (STDIO & SSE transports), dynamic MCP server discovery, permission broker, sandbox execution, Zevon MCP server interface, approvals, action receipts.

Official MCP SDKs (FastMCP), Docker/Podman sandbox, Playwright.

Memory & knowledge

Conversation store, user memory, document index, embeddings and retrieval.

SQLite for desktop; PostgreSQL + pgvector or Qdrant for server.

Storage & jobs

Artifacts, files, task state, background jobs and schedules.

Filesystem, PostgreSQL, Redis optional; Celery/ARQ optional.

Operations

Logs, metrics, traces, evaluations, backups and updates.

OpenTelemetry, Prometheus, Grafana, Langfuse (self-hosted).



6.1 High-level request flow

Microphone listener performs local wake-word detection. Before wake activation, audio remains on-device and is not sent to the model service.

After activation, VAD segments the utterance; ASR converts speech to text and the client shows the transcript.

API authenticates the user and loads the active profile, conversation context and permitted tools.

Router chooses a direct response or an agent workflow. Complex tasks create a task record and a plan with steps, risk labels and expected outputs.

Orchestrator resolves active tools and contextual resources from registered MCP servers and injects their schemas into the model gateway. For specialized or complex multi-step workflows, the orchestrator delegates subtasks to domain sub-agents via the Agent Calling API. Tool calls from models are dispatched to the MCP Host protocol, schema-validated, checked against user/workspace policy, and executed in sandboxes or local environments.

Low-risk tools execute within limits. High-impact actions pause for explicit approval and show a preview of the exact action.

Results are observed and validated; bounded retries or alternative plans may be attempted. Outputs are saved as artifacts.

Assistant returns a concise summary, references/evidence, changed files and any remaining user action. Task and audit records are persisted.

6.2 Task risk levels

Risk

Examples

Policy

R0 — Read-only

Search, summarize, calculate, inspect selected files.

May run automatically within granted scope.

R1 — Reversible local change

Create draft, write new file in chosen workspace, rename selected file.

Preview or undo available; workspace permission required.

R2 — External or destructive

Send email, publish post, delete files, submit form, change account settings.

Require just-in-time explicit confirmation; show target and payload.

R3 — High impact

Payments, legal/financial commitments, security administration, production deployment.

Disabled by default or require separate policy, re-authentication and human review.



7. Recommended open-source technology stack

The stack below is a practical baseline, not a mandate to use every component on day one. Prefer the simplest component that meets a measured requirement. Verify the exact release, model-weight license, bundled assets and transitive dependency licenses before every distribution.

Concern

Recommended choice

Why / notes

Core language

Python 3.12+

Fast AI ecosystem, typing, automation and broad hardware support.

Backend API

FastAPI + Pydantic

Typed REST APIs, async support and OpenAPI generation.

Desktop shell

Tauri 2 + React + TypeScript

Cross-platform desktop app with smaller footprint than Electron; Rust boundary for native permissions.

Web UI

React + Vite + TypeScript

Reuse components for desktop and self-hosted web.

Styling

Tailwind CSS + shadcn/ui (review component licenses)

Fast, accessible UI development; maintain design tokens.

LLM local runtime

Ollama (developer-friendly default)

Easy local model management and API; no paid API required.

LLM performance runtime

llama.cpp / vLLM

llama.cpp for GGUF and CPU/consumer devices; vLLM for GPU server throughput.

Model gateway

Internal provider interface; optional LiteLLM OSS core after license review

Avoid hard dependency on one runtime; keep adapter contract small.

Agent orchestration

LangGraph OR PydanticAI + Agent Calling API

Pick one for MVP. Model workflows as explicit state machines; use standardized Agent Calling API for inter-agent delegation and task checkpoints.

Speech-to-text

faster-whisper or whisper.cpp

Local ASR; whisper.cpp is portable and supports CPU/GPU backends.

Wake word

openWakeWord framework + Zevon-specific model trained with commercially safe data

Check pretrained model licenses: repository code and bundled models may have different terms.

Voice activity detection

Silero VAD

Lightweight speech segmentation; verify model asset license and attribution.

Text-to-speech

Piper (baseline) or Kokoro (quality option)

Local TTS; package voice models only after checking each voice/model license.

Audio I/O

sounddevice / PortAudio; FFmpeg for media conversion

Cross-platform audio capture and media processing; package system codecs carefully.

Primary desktop DB

SQLite + SQLCipher only if encryption integration is validated

Simple local persistence; otherwise encrypt sensitive fields/files at application layer.

Server DB

PostgreSQL

Reliable relational storage, transactions, multi-tenant metadata.

Vector search

pgvector initially; Qdrant for dedicated vector workloads

Avoid adding a separate database before retrieval needs justify it.

Cache / queue

Redis (optional) + ARQ or Celery

Only for server deployments and asynchronous jobs; desktop MVP can use local task queue.

Document parsing

Apache Tika / PyMuPDF / python-docx / openpyxl

Extract content from common office and PDF formats; respect document permissions.

Embeddings

bge-m3 or a suitable multilingual embedding model from a permissive model card

Local embeddings; benchmark retrieval quality and commercial terms.

Browser automation

Playwright

Use isolated browser contexts, domain allowlists and human confirmation.

Code sandbox

Docker or Podman with rootless containers

No host filesystem or network access by default; CPU/RAM/time limits.

MCP runtime (Host & Server)

Official MCP SDKs (`mcp` Python / FastMCP, `@modelcontextprotocol/sdk` TypeScript)

First-class protocol foundation for all tools, context resources, and prompts; enables plug-and-play addition of local/remote tools, community MCP servers, and exposes Zevon to external IDEs.

Agent Calling API & Protocol

Typed JSON-RPC / REST & SSE streaming inter-agent contract

Enables hierarchical agent delegation (orchestrator to specialized sub-agents) and cross-framework agent interoperability.

Auth / SSO

Local OS identity for personal app; Keycloak for business OIDC/SAML

Self-hosted identity provider; avoid building enterprise auth from scratch.

Secrets

OS keychain via keyring; server-side secret store

Never store tokens in plaintext config or logs.

Observability

OpenTelemetry + Prometheus + Grafana

Self-hosted metrics and traces; telemetry opt-in on personal installs.

LLM tracing/evals

Langfuse self-hosted or an internal trace store

Review current license and disable external telemetry.

Packaging

uv + PyInstaller/Nuitka (backend); Tauri bundler (desktop); Docker Compose (server)

Reproducible builds and self-hosting.

CI/CD

GitHub Actions or Forgejo Actions; pytest; Ruff; mypy; Playwright tests

Hosted CI may have free limits; self-host Forgejo runner for zero vendor dependency.

Documentation

MkDocs Material

Developer docs, API docs, plugin authoring guide.



7.1 Official project references

OpenJarvis architecture inspiration: https://github.com/open-jarvis/OpenJarvis

Ollama: https://github.com/ollama/ollama

llama.cpp: https://github.com/ggml-org/llama.cpp

vLLM: https://github.com/vllm-project/vllm

whisper.cpp: https://github.com/ggml-org/whisper.cpp

faster-whisper: https://github.com/SYSTRAN/faster-whisper

openWakeWord: https://github.com/dscripka/openWakeWord

Piper: https://github.com/rhasspy/piper

Kokoro: https://github.com/hexgrad/kokoro

FastAPI: https://github.com/fastapi/fastapi

LangGraph: https://github.com/langchain-ai/langgraph

PydanticAI: https://github.com/pydantic/pydantic-ai

Playwright: https://github.com/microsoft/playwright

Qdrant: https://github.com/qdrant/qdrant

pgvector: https://github.com/pgvector/pgvector

Keycloak: https://github.com/keycloak/keycloak

Model Context Protocol: https://github.com/modelcontextprotocol

8. AI model strategy and hardware profiles

Do not lock Zevon to a single “best model”. Model quality, license, inference speed, context length, tool-calling reliability, multilingual performance and hardware fit change frequently. Build a model registry with versioned model cards and task-specific evaluation scores.

8.1 Model selection policy

Default general assistant: evaluate the current Qwen family and other permissively licensed open-weight models; choose the best model that meets local hardware and quality targets.

Reasoning and complex planning: benchmark current DeepSeek reasoning variants, Qwen reasoning variants and gpt-oss family models where their licenses and hardware requirements fit.

Coding: benchmark Qwen coder variants, Devstral/Mistral coding models and other current code-specialized models against a local repository task suite.

Small/low-memory: use a compact 3B–8B class model for routing, transcription cleanup and simple tasks; do not expect it to handle all complex workflows.

Embeddings: select a multilingual embedding model such as BGE-M3 only after verifying exact weights license and evaluating retrieval on representative documents.

Vision: add a vision-language model only when image/screenshot understanding is in scope; do not route images to text-only models.

8.2 Model deployment profiles

Profile

Indicative hardware

Suggested deployment

Starter / CPU

8–16 GB system RAM, no discrete GPU

Small quantized model via Ollama/llama.cpp; slower responses; use cloud-free, smaller context.

Creator / prosumer

32 GB RAM, 8–16 GB VRAM

7B–14B quantized model; local ASR/TTS; moderate multi-step tasks.

Developer workstation

64 GB RAM, 16–24 GB VRAM

14B–32B quantized model; separate coder model; local embeddings and document index.

Business self-hosted

GPU server(s), 64–256+ GB RAM depending on model

vLLM or SGLang; multi-user scheduling, access control, monitoring and backups.

High-end local

48 GB+ VRAM or multi-GPU

Larger reasoning/coding models; benchmark concurrency, context and throughput.



These are planning bands, not exact minimum specifications. Actual memory use depends on parameter count, quantization, KV cache, context length, concurrency and runtime. Zevon must run a first-launch hardware check and present realistic model choices.

8.3 Model registry fields

Model ID, publisher, exact revision/hash, parameter count, quantization and context limit.

License identifier and license URL for code, weights, tokenizer, datasets where known, and bundled voice assets.

Hardware estimate, supported runtime, languages, modalities and tool/function-call support.

Internal benchmark results: task success, tool-call validity, latency, tokens/sec, memory use and failure rate.

Security review status, known limitations, provenance and last-reviewed date.

8.4 Decoupled model and tool evolution via MCP and Agent API

By standardizing all tools and contextual resources on the Model Context Protocol (MCP) and all inter-agent delegations on the Agent Calling API, Zevon completely decouples model evolution from tool and feature development:

Model interchangeability: Any new local model (Ollama/llama.cpp/vLLM) that supports standard function calling or structured JSON output can immediately consume all existing and future Zevon tools without writing custom glue code.

Zero-code tool addition: New external APIs, local CLI utilities, databases, and workspace integrations can be added simply as standalone MCP servers (local STDIO processes or SSE microservices). Zevon dynamically ingests their tool schemas and exposes them to the active model.

Specialized agent composition: Future complex capabilities (e.g., deep research, automated coding, data analytics) can be introduced as modular sub-agents invoked through the Agent Calling API rather than overloading a single prompt context.

9. Security, privacy and safety design

9.1 Threat model

Prompt injection in web pages, PDFs, emails, code comments and MCP tool output.

Malicious or compromised plugins and MCP servers.

Over-permissioned file, shell, browser or network tools.

Secret leakage through prompts, logs, traces, crash dumps or generated artifacts.

Unintended destructive actions caused by model misunderstanding or hallucinated targets.

Cross-user or cross-tenant data exposure in business deployments.

9.2 Mandatory controls

Control

Implementation requirement

Permission scopes

Every tool declares read/write/network/system scopes; grant per user, workspace and organization.

Sandbox

Code execution runs in disposable, non-root containers with read-only base image, explicit mounts, CPU/RAM/time caps and network disabled by default.

Approval gate

Require explicit approval for sending, publishing, purchasing, deleting, installing, committing, deploying or changing account/security settings.

Prompt-injection defense

Treat retrieved content as untrusted data, never as policy; separate instructions from tool output; enforce permissions outside the LLM.

Secret handling

OS keychain or server secret store; redact tokens and credentials; never add secrets to vector index.

Audit

Record user, task, tool, arguments summary, approval, result, timestamps and artifact hashes; provide retention controls.

Tenant isolation

Enforce tenant ID in every query and storage path; add automated cross-tenant access tests.

Updates

Pin dependencies, generate SBOM, scan vulnerabilities, sign release artifacts and publish security advisories.

Data controls

Local-only mode, retention settings, export/delete, backup/restore and opt-in telemetry.

Fail-safe

On uncertain identity, permissions, target or outcome, stop and ask; never infer approval.



9.3 Privacy defaults

Wake-word processing is local; no always-on audio upload or remote microphone streaming.

Conversation history, memory and documents are stored locally for personal mode.

Remote web access is performed only when requested or enabled; show when network access occurs.

Do not train or fine-tune models on user content by default.

Provide “temporary session” mode that does not persist conversation memory.

Provide business administrators with retention, encryption, backup and audit policy settings.

10. UX and interaction requirements

Screen / surface

Required capabilities

Onboarding

Hardware scan, download/select model, choose voice, test mic/speaker, configure wake phrase, select profile and privacy mode.

Assistant home

Text input, mic state, push-to-talk, model status, offline indicator, conversation list and quick actions.

Voice overlay

Visible listening/thinking/speaking states, transcript, cancel/interrupt, mute and privacy indicator.

Task workspace

Plan, step status, tool activity, approvals, logs summary, artifacts, diffs and retry/cancel controls.

Memory center

View/edit/delete facts, inspect source, pause memory, export and clear selected/all memory.

Tool & plugin manager

Description, publisher, version, permissions, requested scopes, enable/disable and uninstall.

Model manager

Installed/downloadable models, license summary, size, hardware fit, benchmark and active model.

Admin console

Users, roles, policies, audit, deployment health, model routing and retention settings.



10.1 Voice states

The voice UI must distinguish at least: Idle/armed, Wake detected, Listening, Transcribing, Thinking, Waiting for approval, Speaking, Interrupted, Error and Microphone unavailable. Use both visual and audible feedback; never imply the microphone is off when the wake listener is active.

11. API and extensibility requirements

11.1 Core API surface

Endpoint / channel

Purpose

POST /api/v1/chat

Submit text turn; support streaming response.

WS /api/v1/realtime

Stream audio/transcript/response events and interrupt signals.

POST /api/v1/tasks

Create an asynchronous multi-step task.

GET /api/v1/tasks/{id}

Read task state, progress and result.

POST /api/v1/tasks/{id}/approve

Approve or reject a pending action with user identity.

POST /api/v1/tasks/{id}/cancel

Cancel task and terminate child processes.

GET/POST /api/v1/tools

List tools and manage user-authorized tool availability across all connected MCP servers.

GET/POST /api/v1/mcp/servers

List, register, connect, or disconnect MCP servers (STDIO and SSE/HTTP).

POST /api/v1/agents/invoke

Agent Calling API: delegate a specialized subtask to an agent or worker with bounded permissions and event streaming.

GET /api/v1/mcp/sse

Zevon MCP Server endpoint: exposes Zevon capabilities, memory, and tools to external clients (e.g., Antigravity, Cursor, VS Code).

GET/POST /api/v1/memory

Inspect and manage user memory.

GET/POST /api/v1/models

List, select and configure model profiles.

GET /api/v1/health

Health, dependency and runtime readiness.



11.2 Extensibility contract: MCP servers and Agent Calling protocol

Zevon standardizes on the open Model Context Protocol (MCP) and structured Agent Calling APIs as its primary extensibility model, replacing proprietary plugin interfaces:

MCP-native tools: Any tool, data source, or prompt template is implemented as a standard MCP server (STDIO process, SSE endpoint, or Docker container). Zevon acts as an MCP Host, dynamically querying capabilities, schemas, and resource definitions.

Agent Calling API: Specialized capabilities (e.g., Coder Agent, Web Research Agent, Document Specialist) expose standardized agent invocation endpoints. The main orchestrator delegates subtasks to them using typed JSON-RPC/SSE contracts with isolated workspaces and checkpoints.

Ecosystem compatibility: Any community MCP server (e.g. Postgres, Git, Filesystem, Brave Search, Puppeteer, Slack) can be installed and connected directly without custom wrappers.

Security & sandboxing: Each MCP server declares requested scopes (filesystem paths, network domains, system commands). The permission broker validates each tool call prior to dispatching to the MCP process.

Developer experience: Official Python SDK (`mcp` / FastMCP) and TypeScript SDK; scaffolding templates, local mock testing harness, and live MCP inspector.

Zevon as MCP Server: Zevon can itself run as an MCP server, allowing external AI coding assistants and orchestrators to leverage Zevon's voice engine, local memory, and customized local tools.

12. Testing and acceptance criteria

Test area

Acceptance criteria

Wake word

Detect Zevon phrase with measured false-accept/false-reject rates in quiet and noisy environments; provide threshold calibration and push-to-talk fallback.

Voice pipeline

Transcribe supported test utterances, display transcript, speak response and support cancellation; no audio leaves device in local-only mode.

Assistant quality

Pass curated task suite for factual Q&A, summarization, extraction, planning and refusal/clarification cases.

Tool safety

Unauthorized tool call is blocked even if model requests it; R2/R3 actions cannot execute without required approval.

Complex tasks

Task state survives app restart; bounded retries; user can cancel; final output includes artifacts and evidence.

Memory

User can inspect, correct, export and delete stored memory; deleted items are not returned by retrieval.

RAG

Answers include source references; test retrieval precision/recall on representative PDFs and office files.

Security

Sandbox escape tests, prompt-injection tests, tenant-isolation tests, dependency scans and secret-leak checks pass.

Cross-platform

Install, upgrade, uninstall, audio devices, model runtime and core flows tested on supported OS matrix.

Performance

Publish benchmark results for cold start, warm response latency, memory, tokens/sec and concurrent users.



12.1 MVP exit criteria

Desktop app installs and runs on at least Windows and Linux; macOS supported as a release candidate if resources permit.

Local LLM chat works through Ollama or llama.cpp with at least two interchangeable model profiles.

Wake-word activation, local ASR and local TTS work end-to-end, with a documented fallback.

Core tools (calculator, notes, selected-folder file search/read/write) work through permission checks and standard MCP tool interfaces.

Multi-step task runner supports plan, progress, cancellation, approval and final report.

User data is local by default; export/delete and temporary session controls work.

Automated tests cover all P0 requirements and critical safety paths.

13. Delivery roadmap and phases

Suggested roadmap for a small experienced team: approximately 20–28 weeks to a credible public beta, depending on team size, target operating systems and available hardware. Phase durations are estimates; each phase ends with a demonstrable gate.

Phase

Duration

Scope / deliverables

Exit gate

0. Discovery & architecture

1–2 weeks

Finalize personas, task taxonomy, threat model, supported OS, hardware tiers, license policy, UX flows and architecture decision records.

Approved SRS, architecture diagrams, risk register and test plan.

1. Foundation & local chat

2–3 weeks

Repo structure, CI, Tauri shell, React UI, FastAPI, local DB, model adapter, Ollama integration, streaming chat, settings and logs.

Installable app; local chat works offline with one model; tests and docs.

2. Voice assistant

2–3 weeks

Mic permissions, local wake phrase, custom Zevon wake model, VAD, ASR, TTS, voice states, push-to-talk and interruption.

End-to-end voice loop works locally; false activation/latency measured.

3. MCP Tools, Agent API & Task Orchestration

3–4 weeks

MCP Host client, tool registry, permission broker, task state machine, Agent Calling API, planner, core MCP tools (calculator, notes, file tools), approvals, cancellation and audit trail.

A multi-step task can complete safely and recover from failures.

4. Memory & knowledge

2–3 weeks

Conversation memory, user facts, document ingestion, embeddings, vector retrieval, citations, export/delete controls.

RAG test set passes target quality; memory controls verified.

5. MCP Ecosystem & Developer Platform

2–3 weeks

MCP SDK integration (FastMCP), Zevon MCP server endpoint, third-party MCP connection manager, tool test harness, docs, sample tools, and sub-agent templates.

Third-party developer builds and installs a sandboxed sample MCP tool or connects an external agent.

6. Business & creator workflows

3–4 weeks

Profiles, reusable workflow templates, team roles, shared knowledge, admin policy, creator pipelines and self-hosted deployment.

Pilot users complete role-specific workflows; tenant/security checks pass.

7. Hardening & public beta

3–4 weeks

Performance tuning, accessibility, localization, telemetry opt-in, update system, packaging, SBOM, security review, docs and release process.

Release candidate passes acceptance suite; published support matrix and known limitations.



13.1 Suggested MVP scope (first 8–10 weeks)

Keep the first release deliberately narrow: desktop chat, one local model runtime, local wake word + ASR + TTS, calculator/notes/selected-folder tools, a small task orchestrator, explicit approvals, and privacy controls. Defer enterprise SSO, autonomous schedules, broad browser automation, multi-agent collaboration and marketplace features until the core loop is reliable.

13.2 Team composition

Role

Suggested allocation

Responsibilities

Product/UX lead

0.5–1 FTE

Requirements, workflows, user testing, prioritization and acceptance.

Python/AI engineer

1–2 FTE

Model gateway, orchestration, tools, memory, speech and evaluation.

Frontend/desktop engineer

1 FTE

Tauri, React, audio UI, settings, task timeline and packaging.

Platform/security engineer

0.5–1 FTE

Sandbox, auth, deployment, CI/CD, threat model and observability.

QA / automation

0.5–1 FTE

Cross-platform, voice, task, regression and safety testing.



14. Risks, assumptions and constraints

Risk / constraint

Impact

Mitigation

Model weights may not be OSI open source or may carry use restrictions.

Commercial redistribution may be blocked.

Maintain model license allowlist; check exact model card and artifacts; provide multiple alternatives.

Wake-word pretrained model license may be non-commercial.

Commercial Zevon distribution could violate terms.

Use openWakeWord framework only after review; train Zevon model on commercially cleared/self-collected data; audit datasets and weights.

Local hardware varies widely.

Slow responses, memory errors or unsupported models.

Hardware scan, quantization, small-model fallback and honest capability display.

Speech quality varies by accent, language and environment.

Poor hands-free experience.

Benchmark target accents/languages; adjustable thresholds; push-to-talk; user correction feedback.

Agent hallucination or tool misuse.

Data loss, wrong messages or unintended external actions.

Policy enforcement outside model, approvals, sandbox, evidence and reversible workflows.

Open-source project licenses change or have exceptions.

Unexpected compliance obligations.

Pin versions, maintain SBOM, legal review for distribution and re-check licenses at release.

“Any task” expectation is unbounded.

Scope creep and user disappointment.

Publish supported capability matrix; plugin architecture; explicit unsupported-task messaging.

Zero paid software does not mean zero operating cost.

Hardware, electricity, hosting, domains and staff still cost money.

Self-host locally; no mandatory paid services; disclose optional infrastructure costs.



14.1 Assumptions

Initial target is a desktop-first product, with self-hosted team deployment added after MVP.

Users can download model weights and have sufficient disk space; models are not bundled in the installer by default.

Internet access may be needed for initial downloads and web research, but core assistant functions remain local.

Zevon will not silently use a paid cloud API or send user content to a third party.

All model, voice, plugin and dependency licenses will be checked for the intended distribution and commercial use.

15. Definition of done and launch checklist

All P0 requirements implemented and traceable to automated or documented manual tests.

Local-only mode verified with outbound network blocked after installation/model download.

Wake-word model and all bundled voice/model assets have documented commercial-use rights.

Tool permissions and approval gates enforced server-side, not merely by prompt instructions.

Sandbox, secrets, audit logs, export/delete, backup and restore tested.

Cross-platform installers, upgrade/uninstall path and recovery instructions published.

SBOM, third-party notices, model cards, licenses, privacy policy and security contact published.

Developer docs include local setup, architecture, API reference, plugin tutorial and example plugin.

Known limitations, hardware requirements, model recommendations and benchmark methodology published.

Public beta feedback channel and vulnerability disclosure process established.

16. References and license due diligence

The project should use the following as starting points for implementation research. These references are not blanket endorsements of every bundled model, voice, dataset, plugin or optional hosted feature. Review the exact version and license before copying code or distributing assets.

OpenJarvis architecture inspiration: https://github.com/open-jarvis/OpenJarvis

Ollama: https://github.com/ollama/ollama

llama.cpp: https://github.com/ggml-org/llama.cpp

vLLM: https://github.com/vllm-project/vllm

whisper.cpp: https://github.com/ggml-org/whisper.cpp

faster-whisper: https://github.com/SYSTRAN/faster-whisper

openWakeWord: https://github.com/dscripka/openWakeWord

Piper: https://github.com/rhasspy/piper

Kokoro: https://github.com/hexgrad/kokoro

FastAPI: https://github.com/fastapi/fastapi

LangGraph: https://github.com/langchain-ai/langgraph

PydanticAI: https://github.com/pydantic/pydantic-ai

Playwright: https://github.com/microsoft/playwright

Qdrant: https://github.com/qdrant/qdrant

pgvector: https://github.com/pgvector/pgvector

Keycloak: https://github.com/keycloak/keycloak

Model Context Protocol: https://github.com/modelcontextprotocol

Additional research references:

OpenJarvis project documentation: https://open-jarvis.github.io/OpenJarvis/

OpenJarvis architecture overview: https://github.com/open-jarvis/OpenJarvis/blob/main/docs/architecture/overview.md

Hugging Face open model licensing and local model guide (community article; verify claims against model cards): https://huggingface.co/blog/daya-shankar/open-source-llm-models

whisper.cpp capabilities and MIT license: https://github.com/ggml-org/whisper.cpp

openWakeWord repository and license notes: https://github.com/dscripka/openWakeWord

Appendix A — Suggested repository layout

```text
zevon/
  apps/
    desktop/                 # Tauri 2 + React + TypeScript client
    web/                     # Optional self-hosted web client
  services/
    api/                     # FastAPI routes, auth, WebSocket events, Agent Calling API
    assistant/               # Agent orchestration, state machine, sub-agent router
    mcp_broker/              # MCP Host manager, STDIO/SSE client connections, schema ingestion
    mcp_server/              # Zevon's exposed MCP server endpoint for external IDEs/agents
    voice/                   # Wake word, VAD, ASR, TTS
    model_gateway/           # Model registry, provider adapters (Ollama, llama.cpp, vLLM)
    tool_runtime/            # Policy broker, permission guards, Docker/Podman sandbox
    memory/                  # Conversation memory, RAG, and vector indexing
  packages/
    agent-protocol/          # Typed Agent-to-Agent schemas, event contracts, and calling API
    mcp-sdk/                 # MCP helper libraries, tool decorators, and test harnesses
    shared-schemas/          # Pydantic / JSON schemas and shared contracts
    ui/                      # Shared design system components (Tailwind + shadcn/ui)
  plugins/
    mcp-core/                # Built-in MCP servers: calculator, notes, files, time
    examples/                # Sample developer MCP servers and sub-agents
  infra/
    docker/                  # Self-hosted Docker Compose deployment
    monitoring/              # Prometheus, Grafana, OpenTelemetry configs
  docs/
    architecture/
    api/
    mcp-development/
    security/
  tests/
    unit/
    integration/
    e2e/
    evaluations/
  scripts/
  LICENSE
  THIRD_PARTY_NOTICES.md
  MODEL_CARDS.md
  SECURITY.md
  CONTRIBUTING.md
```

Appendix B — Core architectural decisions to lock before coding

Desktop-first or web-first: recommendation is desktop-first with a web UI later, because wake-word and OS actions are core differentiators.

Extensibility architecture: MCP and Agent Calling API locked from Day 1. Standardize all internal tools, third-party extensions, and inter-agent delegations on Model Context Protocol (MCP) and standardized Agent APIs. This ensures any future model (local open-weights or external), external tool (community MCP servers), or specialized sub-agent can be added without modifying core orchestrator code.

Local runtime baseline: Ollama for the easiest first-run experience; retain llama.cpp and vLLM adapters.

Agent framework: select LangGraph or PydanticAI after a one-week spike; do not combine multiple orchestration frameworks in MVP.

Wake word: train a Zevon-specific model with a cleanly licensed dataset and validate false activations in realistic environments.

Database: SQLite for personal mode; PostgreSQL + pgvector for team deployment; add Qdrant only if measured scale warrants it.

Security boundary: all tool calls pass through an MCP policy broker; the LLM never receives direct unrestricted shell or filesystem access.

Commercial license policy: prefer Apache-2.0, MIT, BSD or similarly permissive code and model licenses; review non-code assets independently.