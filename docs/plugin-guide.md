# Zevon Extensions: plugin guide
An extension is a Python file that registers tools. Drop it in `plugins/<name>/plugin.py` (or `plugins/<name>.py`) and restart. It must define `register(registry)`.

```python
# plugins/weather/plugin.py
import httpx

def register(registry):
    @registry.tool(
        "weather_now", "Current temperature for a city.",
        {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
        risk="read",
    )
    def weather_now(city: str):
        r = httpx.get("https://wttr.in/" + city, params={"format": "3"}, timeout=10)
        return r.text
```
**Choosing `risk`:** `read` = only fetches data; `safe_write` = reversible/low impact; `sensitive` = sends, deletes, spends, or changes things others see (needs your approval). When unsure, use `sensitive`.
**Rules:** return a string (or JSON-serializable); raise exceptions freely (the agent sees the error); never trust tool *inputs* (they come from an LLM that may have read a malicious email); validate paths and URLs (see `integrations/system/filesystem.safe_path` and `tools/browser.check_url`).
**Security:** extensions run with full Python access on your machine. Only install code you have read.
**Built-in extensions** live in `backend/app/integrations/` and use the same API. Load order: built-ins → `plugins/` → MCP servers.

## MCP servers
Create `data/mcp_servers.json`:
```json
{"servers": {"files": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/me/docs"], "read_tools": ["read_file"]}}}
```
Tools appear as `mcp_<server>_<tool>`. They default to `sensitive` (approval needed); list harmless ones in `read_tools` or set `"risk": "read"` for the whole server.
