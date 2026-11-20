"""MCP Server Manager: Discovers, connects, and bridges external MCP servers into Zevon."""

import logging
from typing import Any

from packages.shared_schemas.models import RiskLevel
from services.mcp.client import MCPClient, MCPProxyTool
from services.memory.repository import MemoryRepository
from services.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class MCPServerManager:
    """Manages connections to third-party and local MCP servers."""

    def __init__(self, tool_registry: ToolRegistry, repository_factory=None):
        self.tool_registry = tool_registry
        self.repository_factory = repository_factory
        self.clients: dict[str, MCPClient] = {}
        self._server_tools: dict[str, list[str]] = {}  # server_id -> list of tool_names

    async def _get_repo(self) -> MemoryRepository | None:
        if self.repository_factory:
            return await self.repository_factory()
        return None

    async def list_servers(self) -> list[dict[str, Any]]:
        """List configured MCP servers and their connection statuses."""
        repo = await self._get_repo()
        servers = await repo.list_mcp_servers() if repo else []
        results = []
        for s in servers:
            sid = s["id"]
            client = self.clients.get(sid)
            is_conn = client.is_connected if client else False
            tool_count = len(self._server_tools.get(sid, []))
            results.append(
                {
                    **s,
                    "connected": is_conn,
                    "active_tools_count": tool_count,
                    "tools": self._server_tools.get(sid, []),
                }
            )
        return results

    async def register_server(
        self,
        name: str,
        transport: str,
        command: str | None = None,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        url: str | None = None,
        auto_connect: bool = True,
    ) -> dict[str, Any]:
        """Save and optionally connect an external MCP server."""
        repo = await self._get_repo()
        if not repo:
            raise RuntimeError("Repository not available to persist MCP server configuration.")

        server_record = await repo.save_mcp_server(
            name=name,
            transport=transport,
            command=command,
            args=args,
            env=env,
            url=url,
        )

        sid = server_record["id"]
        if auto_connect:
            try:
                await self.connect_server(sid)
            except Exception as e:
                logger.error("Failed to connect MCP server '%s': %s", name, e)

        return server_record

    async def connect_server(self, server_id: str) -> bool:
        """Connect to an MCP server, query tools, and register them into ToolRegistry."""
        repo = await self._get_repo()
        if not repo:
            return False

        servers = await repo.list_mcp_servers()
        target = next((s for s in servers if s["id"] == server_id), None)
        if not target:
            raise KeyError(f"MCP server '{server_id}' not found.")

        # Disconnect existing if any
        if server_id in self.clients:
            await self.disconnect_server(server_id)

        client = MCPClient(
            server_id=target["id"],
            name=target["name"],
            transport=target["transport"],
            command=target["command"],
            args=target["args"],
            env=target["env"],
            url=target["url"],
        )

        await client.connect()
        self.clients[server_id] = client

        # Discover tools
        tools_list = await client.list_tools()
        registered_names = []
        for raw_tool in tools_list:
            # Infer risk level: default R1, if name contains delete/destroy/write/exec
            t_name = raw_tool.get("name", "")
            risk = RiskLevel.R1
            if any(k in t_name.lower() for k in ["delete", "remove", "drop", "destroy", "kill"]):
                risk = RiskLevel.R2
            elif any(k in t_name.lower() for k in ["read", "get", "list", "search", "query", "find"]):
                risk = RiskLevel.R0

            proxy = MCPProxyTool(mcp_client=client, raw_tool=raw_tool, risk_level=risk)
            self.tool_registry.register_tool(proxy)
            registered_names.append(proxy.name)

        self._server_tools[server_id] = registered_names
        logger.info("Registered %d tools from MCP server '%s'", len(registered_names), target["name"])
        return True

    async def disconnect_server(self, server_id: str) -> bool:
        """Disconnect server and remove its tools from ToolRegistry."""
        client = self.clients.pop(server_id, None)
        if client:
            await client.disconnect()

        tool_names = self._server_tools.pop(server_id, [])
        for name in tool_names:
            self.tool_registry.unregister_tool(name)

        return True

    async def delete_server(self, server_id: str) -> bool:
        """Disconnect and delete MCP server from database."""
        await self.disconnect_server(server_id)
        repo = await self._get_repo()
        if repo:
            return await repo.delete_mcp_server(server_id)
        return False
