"""MCP client: exposes tools from MCP servers (stdio) as Zevon tools.
Config: data/mcp_servers.json  {"servers": {"name": {"command": "...", "args": [...], "env": {}, "risk": "sensitive", "read_tools": ["tool"]}}}
Tools default to risk=sensitive (approval required) unless listed in read_tools or risk is set per server."""
import asyncio
import json
import re
import threading
from pathlib import Path

from ..config import settings


def _run_sync(coro_fn, *args, timeout=60):
    """Run an async MCP call in a fresh thread (safe inside uvicorn's running event loop)."""
    box = {}

    def target():
        try:
            box["r"] = asyncio.run(coro_fn(*args))
        except BaseException as e:  # noqa: BLE001
            box["e"] = e
    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        raise TimeoutError("MCP server timed out.")
    if "e" in box:
        raise box["e"]
    return box.get("r")


def _attr(obj, *names, default=None):
    """mcp 1.x uses camelCase (inputSchema, isError); mcp 2.x uses snake_case. Accept both."""
    for n in names:
        if hasattr(obj, n):
            return getattr(obj, n)
    return default


def _params(cfg):
    from mcp import StdioServerParameters
    return StdioServerParameters(command=cfg["command"], args=cfg.get("args", []), env=cfg.get("env") or None)


async def _list_tools(cfg):
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    async with stdio_client(_params(cfg)) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            return (await s.list_tools()).tools


async def _call_tool(cfg, tool, args):
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    async with stdio_client(_params(cfg)) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool(tool, args)
            text = "\n".join(c.text for c in res.content if hasattr(c, "text"))
            return ("MCP tool error: " if _attr(res, "isError", "is_error", default=False) else "") + text


def register_mcp(registry, store=None) -> list[str]:
    path = Path(settings.mcp_config)
    if not path.exists():
        return []
    try:
        import mcp  # noqa: F401
    except ImportError:
        if store:
            store.audit("mcp", "load", "pip install mcp", "skipped")
        return []
    names = []
    for server, cfg in json.loads(path.read_text()).get("servers", {}).items():
        try:
            tools = _run_sync(_list_tools, cfg)
        except Exception as e:
            if store:
                store.audit("mcp", server, str(e)[:300], "connect failed")
            continue
        for t in tools:
            risk = "read" if t.name in cfg.get("read_tools", []) else cfg.get("risk", "sensitive")
            name = re.sub(r"\W", "_", f"mcp_{server}_{t.name}")

            def func(_cfg=cfg, _tool=t.name, **kw):
                return _run_sync(_call_tool, _cfg, _tool, kw)
            registry.tool(name, f"[MCP:{server}] {t.description or t.name}", _attr(t, "inputSchema", "input_schema") or
                          {"type": "object", "properties": {}}, risk=risk)(func)
            names.append(name)
    return names
