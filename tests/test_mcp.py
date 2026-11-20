"""Unit and integration tests for MCP Host, Zevon MCP Server, and Agent Calling API."""

import pytest
from pathlib import Path

from packages.agent_protocol.protocol import AgentTaskRequest
from services.agents.dispatcher import AgentDispatcher
from services.mcp.server_manager import MCPServerManager
from services.mcp.zevon_server import ZevonMCPServer
from services.memory.database import create_connection
from services.memory.repository import MemoryRepository
from services.tools.registry import get_default_tool_registry


@pytest.fixture
def temp_workspace(tmp_path: Path):
    ws = tmp_path / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


@pytest.mark.asyncio
async def test_zevon_mcp_server_protocol(temp_workspace: Path, temp_db_path: str):
    async def repo_factory():
        conn = await create_connection(temp_db_path)
        return MemoryRepository(conn)

    tools = get_default_tool_registry(allowed_workspaces=[temp_workspace], repository_factory=repo_factory)
    server = ZevonMCPServer(tool_registry=tools, repository_factory=repo_factory)

    # 1. Initialize Handshake
    init_res = await server.handle_rpc(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
        }
    )
    assert init_res["result"]["serverInfo"]["name"] == "zevon-mcp-server"
    assert "tools" in init_res["result"]["capabilities"]

    # 2. Tools List
    list_res = await server.handle_rpc(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    )
    tools_list = list_res["result"]["tools"]
    assert len(tools_list) >= 8
    tool_names = [t["name"] for t in tools_list]
    assert "calculator" in tool_names
    assert "file_read" in tool_names

    # 3. Tools Call (Calculator)
    call_res = await server.handle_rpc(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "calculator", "arguments": {"expression": "7 * 8"}},
        }
    )
    assert call_res["result"]["isError"] is False
    assert "56" in call_res["result"]["content"][0]["text"]

    # 4. Resources List
    res_list = await server.handle_rpc(
        {"jsonrpc": "2.0", "id": 4, "method": "resources/list", "params": {}}
    )
    uris = [r["uri"] for r in res_list["result"]["resources"]]
    assert "zevon://notes" in uris
    assert "zevon://conversations" in uris

    # 5. Resources Read
    res_read = await server.handle_rpc(
        {"jsonrpc": "2.0", "id": 5, "method": "resources/read", "params": {"uri": "zevon://notes"}}
    )
    assert "contents" in res_read["result"]


@pytest.mark.asyncio
async def test_mcp_server_manager(temp_workspace: Path, temp_db_path: str):
    async def repo_factory():
        conn = await create_connection(temp_db_path)
        return MemoryRepository(conn)

    tools = get_default_tool_registry(allowed_workspaces=[temp_workspace])
    mgr = MCPServerManager(tool_registry=tools, repository_factory=repo_factory)

    # Register server without auto_connect
    reg = await mgr.register_server(
        name="test-server",
        transport="stdio",
        command="python",
        args=["-m", "services.mcp.zevon_server"],
        auto_connect=False,
    )
    assert reg["name"] == "test-server"

    servers = await mgr.list_servers()
    assert len(servers) >= 1
    assert servers[0]["name"] == "test-server"
    assert servers[0]["connected"] is False

    # Clean up
    deleted = await mgr.delete_server(reg["id"])
    assert deleted is True


@pytest.mark.asyncio
async def test_agent_dispatcher_and_subagents(temp_workspace: Path):
    tools = get_default_tool_registry(allowed_workspaces=[temp_workspace])
    dispatcher = AgentDispatcher(tool_registry=tools)

    agents = dispatcher.list_agents()
    agent_names = [a["name"] for a in agents]
    assert "coder" in agent_names
    assert "researcher" in agent_names
    assert "document" in agent_names

    # 1. Invoke Coder Agent
    coder_req = AgentTaskRequest(
        target_agent="coder",
        instruction="Verify python script execution",
        context={"code": "print('Code verification OK')"},
    )
    coder_resp = await dispatcher.invoke(coder_req)
    assert coder_resp.status == "success"
    assert "Code verification OK" in coder_resp.result_text

    # 2. Invoke Researcher Agent
    research_req = AgentTaskRequest(
        target_agent="researcher",
        instruction="Local personal AI architectures",
    )
    research_resp = await dispatcher.invoke(research_req)
    assert research_resp.status == "success"
    assert "research" in research_resp.result_text.lower()

    # 3. Invoke Document Agent
    doc_path = str(temp_workspace / "summary_report.md")
    doc_req = AgentTaskRequest(
        target_agent="document",
        instruction="Generate report",
        context={"path": doc_path, "content": "# Architecture Summary\nLocal first runtime."},
    )
    doc_resp = await dispatcher.invoke(doc_req)
    assert doc_resp.status == "success"
    assert len(doc_resp.artifacts) >= 1
    assert Path(doc_path).exists()
