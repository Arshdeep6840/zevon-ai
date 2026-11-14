#!/usr/bin/env bash
# Usage: ./scripts/push_to_github.sh https://github.com/<you>/zevon-ai.git
# Create the EMPTY repo on github.com first (or use `gh repo create zevon-ai --public`). Needs your git credentials.
set -e
cd "$(dirname "$0")/.."
URL="${1:?usage: $0 <repo-url>}"
git remote remove origin 2>/dev/null || true
git remote add origin "$URL"
git branch -M main
git push -u origin main
echo "Pushed. Add repo topics: ai-assistant, ollama, local-llm, fastapi, self-hosted."
