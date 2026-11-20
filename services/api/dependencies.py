"""FastAPI dependency injection providers."""

from collections.abc import AsyncGenerator
from pathlib import Path

from services.agents.dispatcher import AgentDispatcher
from services.api.config import settings
from services.mcp.server_manager import MCPServerManager
from services.mcp.zevon_server import ZevonMCPServer
from services.memory.database import create_connection, get_db
from services.memory.repository import MemoryRepository
from services.model_gateway.registry import ModelRegistry, get_model_registry
from services.orchestrator.orchestrator import TaskOrchestrator
from services.orchestrator.planner import TaskPlanner
from services.tools.registry import ToolRegistry, get_default_tool_registry

# Global singletons
_tool_registry: ToolRegistry | None = None
_orchestrator: TaskOrchestrator | None = None
_mcp_manager: MCPServerManager | None = None
_zevon_mcp_server: ZevonMCPServer | None = None
_agent_dispatcher: AgentDispatcher | None = None


async def get_repository() -> AsyncGenerator[MemoryRepository, None]:
    """Provide a MemoryRepository backed by an async database connection."""
    async for conn in get_db(settings.db_path):
        yield MemoryRepository(conn)


async def _repo_factory() -> MemoryRepository:
    """Factory helper to obtain a repository instance."""
    conn = await create_connection(settings.db_path)
    return MemoryRepository(conn)


def get_gateway() -> ModelRegistry:
    """Provide the global ModelRegistry instance."""
    return get_model_registry(ollama_url=settings.ollama_url)


def get_tool_registry() -> ToolRegistry:
    """Provide the global ToolRegistry populated with local tools."""
    global _tool_registry
    if _tool_registry is None:
        workspace_root = Path.cwd().resolve()
        _tool_registry = get_default_tool_registry(
            allowed_workspaces=[workspace_root],
            repository_factory=_repo_factory,
        )
    return _tool_registry


def get_orchestrator() -> TaskOrchestrator:
    """Provide the global TaskOrchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        tools = get_tool_registry()
        gateway = get_gateway()
        planner = TaskPlanner(tool_registry=tools, model_gateway=gateway)
        _orchestrator = TaskOrchestrator(
            tool_registry=tools,
            planner=planner,
            repository_factory=_repo_factory,
        )
    return _orchestrator


def get_mcp_manager() -> MCPServerManager:
    """Provide the global MCPServerManager instance."""
    global _mcp_manager
    if _mcp_manager is None:
        tools = get_tool_registry()
        _mcp_manager = MCPServerManager(
            tool_registry=tools,
            repository_factory=_repo_factory,
        )
    return _mcp_manager


def get_zevon_mcp_server() -> ZevonMCPServer:
    """Provide the Zevon dual-role MCP server instance."""
    global _zevon_mcp_server
    if _zevon_mcp_server is None:
        tools = get_tool_registry()
        _zevon_mcp_server = ZevonMCPServer(
            tool_registry=tools,
            repository_factory=_repo_factory,
        )
    return _zevon_mcp_server


def get_agent_dispatcher() -> AgentDispatcher:
    """Provide the global AgentDispatcher instance."""
    global _agent_dispatcher
    if _agent_dispatcher is None:
        tools = get_tool_registry()
        gateway = get_gateway()
        _agent_dispatcher = AgentDispatcher(
            tool_registry=tools,
            model_gateway=gateway,
        )
    return _agent_dispatcher
