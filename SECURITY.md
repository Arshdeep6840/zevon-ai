# Security model
- The LLM never executes anything. It *requests* registered tools; `core/permissions.py` decides: allow, queue for approval, or deny.
- Read/summarize/draft run automatically. Send email, delete files, and moving files need approval in the Approvals tab.
- File tools are limited to `ZEVON_ALLOWED_FOLDERS` (empty = no access).
- Tool output (emails, files, web) is wrapped in `<untrusted_data>` and the system prompt tells the model to treat it as data. This reduces, but does not eliminate, prompt injection risk, which is why sensitive actions require human approval.
- Every action is written to the audit log. The kill switch disables all agent actions.
- Set `ZEVON_API_TOKEN` before exposing the backend. Use Tailscale; never expose port 8000 publicly.
- Browser tool: http(s) only, private/loopback/link-local addresses blocked (also after redirects); optional domain allowlist.
- Terminal tool: allowlisted programs only, no shell, no pipes/redirects, path arguments must be inside authorized folders.
- MCP tools default to *sensitive* (approval required). Extensions in `plugins/` run with full Python access: install only code you trust.
- Email rules: the email body is read through a tool, so it stays marked untrusted; rule actions still pass the permission policy.
- Web Push uses VAPID keys stored in `data/vapid_private.pem`; serve over HTTPS.
- Per-tool permissions can only be changed by the owner through the authenticated API; the agent has no tool for it. Setting a sensitive tool to "run automatically" asks for confirmation in the UI.
- Cloud model providers (openai-compatible remote endpoints, anthropic) send prompts and tool results off-machine; the UI labels the model local or cloud.
- `browser_interact` and `terminal_run_any` (opt-in) always need approval and show the exact action; page actions are a fixed whitelist (no script execution); terminal has no shell and a hard-deny list.
- A repeated-identical-tool-call guard stops runaway loops.
- Known gaps (v0.3): Google token is stored unencrypted in `data/` (protect with disk encryption), DNS-rebinding not mitigated in the browser tool, no rate limiting.
Report vulnerabilities privately to the maintainer.
