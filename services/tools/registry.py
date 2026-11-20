"""Unified Tool Registry and Gateway for Zevon MCP and Built-in Tools."""

from pathlib import Path
from typing import Any

from services.tools.builtin import (
    AppLaunchTool,
    BaseTool,
    CalculatorTool,
    CodeExecutionTool,
    FileDeleteTool,
    FileReadTool,
    FileSearchTool,
    FileWriteTool,
    NotesTool,
    TimeTool,
    WebResearchTool,
)
from services.tools.permissions import PermissionBroker


class ToolRegistry:
    """
    Central catalog of all active tools available to Zevon orchestrators,
    models, and external agents. Enforces permission boundaries across all invocations.
    """

    def __init__(self, permission_broker: PermissionBroker | None = None):
        self._tools: dict[str, BaseTool] = {}
        self.permission_broker = permission_broker or PermissionBroker()

    def register_tool(self, tool: BaseTool) -> None:
        """Register a built-in or MCP tool."""
        self._tools[tool.name] = tool

    def unregister_tool(self, name: str) -> bool:
        """Remove a tool from the catalog."""
        return self._tools.pop(name, None) is not None

    def get_tool(self, name: str) -> BaseTool | None:
        """Retrieve tool by identifier."""
        return self._tools.get(name)

    def list_tools(self) -> list[BaseTool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def export_schemas(self) -> list[dict[str, Any]]:
        """Export tool definitions in function-calling schema format."""
        return [tool.to_schema() for tool in self._tools.values()]

    async def execute_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        is_user_approved: bool = False,
        context: dict[str, Any] | None = None,
    ) -> Any:
        """
        Execute tool through security policy gates and audit logger.
        Raises:
            KeyError: if tool is not registered.
            ApprovalRequiredError: if tool requires user confirmation (R2/R3).
            SecurityViolationError: if path/command is disallowed.
        """
        tool = self.get_tool(name)
        if not tool:
            raise KeyError(f"Tool '{name}' is not registered in the tool gateway.")

        return await tool.execute(
            arguments=arguments,
            permission_broker=self.permission_broker,
            is_user_approved=is_user_approved,
            context=context,
        )


def get_default_tool_registry(
    allowed_workspaces: list[str | Path] | None = None,
    repository_factory=None,
) -> ToolRegistry:
    """Instantiate and populate ToolRegistry with standard local tools."""
    workspaces = [str(w) for w in allowed_workspaces] if allowed_workspaces else [str(Path.cwd())]
    broker = PermissionBroker(allowed_workspaces=workspaces)
    registry = ToolRegistry(permission_broker=broker)

    # Register standard core tools
    registry.register_tool(CalculatorTool())
    registry.register_tool(TimeTool())
    registry.register_tool(NotesTool(repository_factory=repository_factory))
    registry.register_tool(FileSearchTool())
    registry.register_tool(FileReadTool())
    registry.register_tool(FileWriteTool())
    registry.register_tool(FileDeleteTool())
    registry.register_tool(CodeExecutionTool())
    registry.register_tool(AppLaunchTool())
    registry.register_tool(WebResearchTool())

    return registry
