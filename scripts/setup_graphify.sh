#!/usr/bin/env bash
# One-time setup so your AI assistant uses the code graph instead of reading every file.
# The graph itself (graphify-out/) is already committed; this installs the tool and the hooks.
set -e
cd "$(dirname "$0")/.."
if ! command -v graphify >/dev/null; then
  if command -v uv >/dev/null; then uv tool install graphifyy; else pipx install graphifyy; fi
fi
graphify hook install            # rebuild graph automatically on git commit/checkout (this machine)
graphify claude install --project  # Claude Code: CLAUDE.md rules + hooks (already committed; safe to re-run)
# Other assistants: graphify install --platform codex|cursor|gemini|copilot|aider  (see: graphify --help)
graphify update .
echo "Done. Visual graph: graphify-out/graph.html   Summary: graphify-out/GRAPH_REPORT.md"
