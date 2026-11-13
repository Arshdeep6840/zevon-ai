# Instructions for AI coding assistants (Codex, Cursor, Copilot, Aider, Claude Code...)
Do not read the whole repository. Navigate in this order:
1. `docs/CODEMAP.md`: file responsibilities, request flow, "how to add X" recipes, invariants.
2. `graphify query "<question>"`, `graphify explain "<symbol>"`, `graphify path "A" "B"`, `graphify affected "X"` (reads `graphify-out/graph.json`; returns file and line numbers). Install: `uv tool install graphifyy` (or `pipx install graphifyy`).
3. Open only the files/lines those point to. Open `graphify-out/graph.html` in a browser for the visual graph.
After editing code run `graphify update .` (local, free) and, if you changed structure, update `docs/CODEMAP.md`.
Run tests with `cd backend && pytest`. Keep the risk levels and invariants in CODEMAP intact.
