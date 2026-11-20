"""Model Context Protocol (MCP) Client over STDIO and SSE transports."""

import asyncio
import json
import logging
import subprocess
from typing import Any

import httpx

from packages.shared_schemas.models import RiskLevel
from services.tools.builtin import BaseTool
from services.tools.permissions import PermissionBroker

logger = logging.getLogger(__name__)


class MCPClient:
    """
    Client for interacting with any Model Context Protocol (MCP) server.
    Supports STDIO process transport and HTTP Server-Sent Events (SSE) transport.
    """

    def __init__(
        self,
        server_id: str,
        name: str,
        transport: str = "stdio",
        command: str | None = None,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        url: str | None = None,
    ):
        self.server_id = server_id
        self.name = name
        self.transport = transport
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.url = url

        self._process: asyncio.subprocess.Process | None = None
        self._request_counter = 0
        self._pending_requests: dict[int | str, asyncio.Future] = {}
        self._reader_task: asyncio.Task | None = None
        self._is_connected = False
        self.server_info: dict[str, Any] = {}
        self.capabilities: dict[str, Any] = {}

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    async def connect(self) -> None:
        """Establish transport connection and perform MCP initialization handshake."""
        if self._is_connected:
            return

        if self.transport == "stdio":
            if not self.command:
                raise ValueError("Parameter 'command' is required for STDIO MCP transport.")

            cmd = [self.command, *self.args]
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self._reader_task = asyncio.create_task(self._read_stdio_loop())
        elif self.transport == "sse":
            if not self.url:
                raise ValueError("Parameter 'url' is required for SSE MCP transport.")
            # For SSE, HTTP client is used per request
        else:
            raise ValueError(f"Unsupported MCP transport: {self.transport}")

        # Send initialize handshake
        init_response = await self.request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}, "resources": {}},
                "clientInfo": {"name": "zevon-host", "version": "0.1.0"},
            },
        )
        self.server_info = init_response.get("serverInfo", {})
        self.capabilities = init_response.get("capabilities", {})

        # Send initialized notification
        await self.notify("notifications/initialized", {})
        self._is_connected = True
        logger.info("Connected to MCP server '%s' (%s)", self.name, self.server_id)

    async def _read_stdio_loop(self) -> None:
        """Background loop reading JSON-RPC messages from subprocess stdout."""
        if not self._process or not self._process.stdout:
            return

        try:
            while not self._process.stdout.at_eof():
                line = await self._process.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8").strip()
                if not text:
                    continue
                try:
                    data = json.loads(text)
                    if "id" in data and data["id"] in self._pending_requests:
                        fut = self._pending_requests.pop(data["id"])
                        if not fut.done():
                            if "error" in data and data["error"]:
                                fut.set_exception(RuntimeError(data["error"].get("message", "MCP RPC Error")))
                            else:
                                fut.set_result(data.get("result"))
                except json.JSONDecodeError:
                    continue
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Error in MCP stdio reader for %s: %s", self.name, e)

    async def request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """Send a JSON-RPC 2.0 request and wait for the response."""
        self._request_counter += 1
        req_id = self._request_counter
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }

        if self.transport == "stdio":
            if not self._process or not self._process.stdin:
                raise RuntimeError(f"MCP server '{self.name}' stdio process is not running.")

            fut = asyncio.get_running_loop().create_future()
            self._pending_requests[req_id] = fut

            data = json.dumps(payload) + "\n"
            self._process.stdin.write(data.encode("utf-8"))
            await self._process.stdin.drain()

            try:
                return await asyncio.wait_for(fut, timeout=30.0)
            except asyncio.TimeoutError:
                self._pending_requests.pop(req_id, None)
                raise TimeoutError(f"MCP request '{method}' to server '{self.name}' timed out.")
        elif self.transport == "sse":
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(self.url, json=payload)
                res.raise_for_status()
                data = res.json()
                if "error" in data and data["error"]:
                    raise RuntimeError(data["error"].get("message", "MCP RPC Error"))
                return data.get("result")

    async def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        """Send a JSON-RPC 2.0 notification without expecting a response."""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }
        if self.transport == "stdio" and self._process and self._process.stdin:
            data = json.dumps(payload) + "\n"
            self._process.stdin.write(data.encode("utf-8"))
            await self._process.stdin.drain()
        elif self.transport == "sse" and self.url:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(self.url, json=payload)

    async def list_tools(self) -> list[dict[str, Any]]:
        """Query tools/list from the MCP server."""
        res = await self.request("tools/list", {})
        return res.get("tools", []) if isinstance(res, dict) else []

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Execute tools/call on the remote MCP server."""
        res = await self.request("tools/call", {"name": name, "arguments": arguments})
        if isinstance(res, dict) and "content" in res:
            # Standard MCP tool response format
            text_parts = [
                c.get("text", "")
                for c in res.get("content", [])
                if c.get("type") == "text"
            ]
            return "\n".join(text_parts) if text_parts else res
        return res

    async def disconnect(self) -> None:
        """Gracefully close MCP transport connection."""
        self._is_connected = False
        if self._reader_task:
            self._reader_task.cancel()
            self._reader_task = None

        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=3.0)
            except Exception:
                self._process.kill()
            self._process = None


class MCPProxyTool(BaseTool):
    """Wraps an external MCP tool as a native Zevon BaseTool."""

    def __init__(self, mcp_client: MCPClient, raw_tool: dict[str, Any], risk_level: RiskLevel = RiskLevel.R1):
        self.mcp_client = mcp_client
        self.raw_tool = raw_tool
        self.name = raw_tool.get("name", "unknown_mcp_tool")
        self.description = raw_tool.get("description", f"MCP tool from {mcp_client.name}")
        self.risk_level = risk_level
        self.parameters = raw_tool.get("inputSchema", {"type": "object", "properties": {}})

    async def execute(
        self,
        arguments: dict[str, Any],
        permission_broker: PermissionBroker,
        is_user_approved: bool = False,
        context: dict[str, Any] | None = None,
    ) -> Any:
        permission_broker.check_permission(self.name, self.risk_level, arguments, is_user_approved)
        try:
            result = await self.mcp_client.call_tool(self.name, arguments)
            permission_broker.log_action(self.name, arguments, self.risk_level, approved=True, result=result)
            return result
        except Exception as e:
            permission_broker.log_action(
                self.name, arguments, self.risk_level, approved=True, result=str(e), is_error=True
            )
            raise
