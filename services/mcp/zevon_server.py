"""Zevon Dual-Role MCP Server: Exposes Zevon tools and memory to external IDEs and agents."""

import asyncio
import json
import logging
import sys
from typing import Any

from services.memory.database import get_db
from services.memory.repository import MemoryRepository
from services.tools.registry import ToolRegistry, get_default_tool_registry

logger = logging.getLogger(__name__)


class ZevonMCPServer:
    """
    Exposes Zevon's internal tools, notes, and memory as a standard Model Context Protocol (MCP) server.
    Allows external IDEs (Antigravity, Cursor, Claude Code, VS Code) to consume Zevon capabilities.
    """

    PROTOCOL_VERSION = "2024-11-05"

    def __init__(self, tool_registry: ToolRegistry | None = None, repository_factory=None):
        self.tool_registry = tool_registry or get_default_tool_registry()
        self.repository_factory = repository_factory

    async def _get_repo(self) -> MemoryRepository | None:
        if self.repository_factory:
            return await self.repository_factory()
        return None

    async def handle_rpc(self, request: dict[str, Any]) -> dict[str, Any]:
        """Process an incoming JSON-RPC 2.0 request."""
        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        try:
            if method == "initialize":
                result = {
                    "protocolVersion": self.PROTOCOL_VERSION,
                    "serverInfo": {"name": "zevon-mcp-server", "version": "0.1.0"},
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "resources": {"subscribe": False, "listChanged": True},
                    },
                }
            elif method in ("notifications/initialized", "initialized"):
                result = {}
            elif method == "tools/list":
                tools = []
                for t in self.tool_registry.list_tools():
                    tools.append(
                        {
                            "name": t.name,
                            "description": t.description,
                            "inputSchema": t.parameters,
                        }
                    )
                result = {"tools": tools}
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                if not tool_name:
                    raise ValueError("Parameter 'name' is required for tools/call.")

                repo = await self._get_repo()
                context = {"repository": repo}
                raw_out = await self.tool_registry.execute_tool(
                    name=tool_name,
                    arguments=arguments,
                    is_user_approved=True,  # IDE / External host already authorized the call
                    context=context,
                )
                text_content = json.dumps(raw_out, indent=2) if isinstance(raw_out, (dict, list)) else str(raw_out)
                result = {
                    "content": [{"type": "text", "text": text_content}],
                    "isError": False,
                }
            elif method == "resources/list":
                result = {
                    "resources": [
                        {
                            "uri": "zevon://notes",
                            "name": "Local Notes Store",
                            "description": "All personal notes stored locally in Zevon SQLite.",
                            "mimeType": "application/json",
                        },
                        {
                            "uri": "zevon://conversations",
                            "name": "Conversation History",
                            "description": "Recent conversations and assistant interactions.",
                            "mimeType": "application/json",
                        },
                    ]
                }
            elif method == "resources/read":
                uri = params.get("uri", "")
                repo = await self._get_repo()
                if uri == "zevon://notes":
                    notes = await repo.list_notes() if repo else []
                    result = {
                        "contents": [
                            {"uri": uri, "mimeType": "application/json", "text": json.dumps(notes, indent=2)}
                        ]
                    }
                elif uri == "zevon://conversations":
                    convs = await repo.list_conversations() if repo else []
                    convs_data = [c.model_dump(mode="json") for c in convs]
                    result = {
                        "contents": [
                            {"uri": uri, "mimeType": "application/json", "text": json.dumps(convs_data, indent=2)}
                        ]
                    }
                else:
                    raise ValueError(f"Resource URI not found: {uri}")
            elif method == "ping":
                result = {}
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }

            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        except Exception as e:
            logger.error("Error handling MCP RPC '%s': %s", method, e)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": str(e)},
            }

    async def run_stdio(self) -> None:
        """Run MCP server in STDIO transport mode."""
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_running_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        while not reader.at_eof():
            line = await reader.readline()
            if not line:
                break
            text = line.decode("utf-8").strip()
            if not text:
                continue
            try:
                req = json.loads(text)
                res = await self.handle_rpc(req)
                sys.stdout.write(json.dumps(res) + "\n")
                sys.stdout.flush()
            except Exception as e:
                logger.error("STDIO loop error: %s", e)


async def main():
    async def repo_factory():
        async for conn in get_db():
            return MemoryRepository(conn)

    server = ZevonMCPServer(repository_factory=repo_factory)
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
