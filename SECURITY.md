# Security model
- The LLM never executes anything. It *requests* registered tools; `core/permissions.py` decides: allow, queue for approval, or deny.
- Read/summarize/draft run automatically. Send email, delete files, and moving files need approval in the Approvals tab.
- File tools are limited to `ZEVON_ALLOWED_FOLDERS` (empty = no access).
- Tool output (emails, files, web) is wrapped in `<untrusted_data>` and the system prompt tells the model to treat it as data. This reduces, but does not eliminate, prompt injection risk, which is why sensitive actions require human approval.
- Every action is written to the audit log. The kill switch disables all agent actions.
- Set `ZEVON_API_TOKEN` before exposing the backend. Use Tailscale; never expose port 8000 publicly.
- Known gaps (v0.1): Google token is stored unencrypted in `data/` (protect with disk encryption), no terminal tool yet, no rate limiting.
Report vulnerabilities privately to the maintainer.
