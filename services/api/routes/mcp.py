"""Model Context Protocol (MCP) Host and Server API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from services.api.dependencies import get_mcp_manager, get_zevon_mcp_server
from services.mcp.server_manager import MCPServerManager
from services.mcp.zevon_server import ZevonMCPServer

router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])


class RegisterMCPServerRequest(BaseModel):
    name: str
    transport: str = Field(default="stdio", description="'stdio' or 'sse'")
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    url: str | None = None
    auto_connect: bool = True


@router.get("/servers")
async def list_mcp_servers(
    mcp_manager: MCPServerManager = Depends(get_mcp_manager),
):
    """List configured and connected external MCP servers."""
    return await mcp_manager.list_servers()


@router.post("/servers")
async def register_mcp_server(
    req: RegisterMCPServerRequest,
    mcp_manager: MCPServerManager = Depends(get_mcp_manager),
):
    """Register and connect an external MCP server."""
    try:
        return await mcp_manager.register_server(
            name=req.name,
            transport=req.transport,
            command=req.command,
            args=req.args,
            env=req.env,
            url=req.url,
            auto_connect=req.auto_connect,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/servers/{server_id}/connect")
async def connect_mcp_server(
    server_id: str,
    mcp_manager: MCPServerManager = Depends(get_mcp_manager),
):
    """Connect to a registered MCP server and ingest its tools."""
    try:
        ok = await mcp_manager.connect_server(server_id)
        return {"server_id": server_id, "connected": ok}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/servers/{server_id}/disconnect")
async def disconnect_mcp_server(
    server_id: str,
    mcp_manager: MCPServerManager = Depends(get_mcp_manager),
):
    """Disconnect an active MCP server and remove its tools."""
    ok = await mcp_manager.disconnect_server(server_id)
    return {"server_id": server_id, "disconnected": ok}


@router.delete("/servers/{server_id}")
async def delete_mcp_server(
    server_id: str,
    mcp_manager: MCPServerManager = Depends(get_mcp_manager),
):
    """Delete an MCP server registration."""
    ok = await mcp_manager.delete_server(server_id)
    return {"server_id": server_id, "deleted": ok}


# --- Dual-Role Zevon MCP Server Endpoints ---


@router.get("/sse")
async def zevon_mcp_sse(
    request: Request,
):
    """Server-Sent Events endpoint exposing Zevon capabilities to external IDEs."""
    async def sse_stream():
        # MCP SSE handshake event specifying endpoint for messages
        base_url = str(request.base_url).rstrip("/")
        yield f"event: endpoint\ndata: {base_url}/api/v1/mcp/messages\n\n"

    return StreamingResponse(
        sse_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/messages")
async def zevon_mcp_messages(
    request_data: dict[str, Any],
    zevon_server: ZevonMCPServer = Depends(get_zevon_mcp_server),
):
    """Handle incoming JSON-RPC 2.0 requests from external IDEs and agents."""
    return await zevon_server.handle_rpc(request_data)
