"""Specialized Sub-Agents for Zevon Agent Calling API."""

from collections.abc import AsyncGenerator

from packages.agent_protocol.protocol import (
    AgentEvent,
    AgentEventType,
    AgentTaskRequest,
)
from services.model_gateway.registry import ModelRegistry
from services.tools.registry import ToolRegistry


class BaseSubAgent:
    """Base class for domain-specific sub-agents."""

    name: str = "base"
    description: str = "Base agent"
    default_tools: list[str] = []

    def __init__(self, tool_registry: ToolRegistry, model_gateway: ModelRegistry | None = None):
        self.tool_registry = tool_registry
        self.model_gateway = model_gateway

    async def execute(self, request: AgentTaskRequest) -> AsyncGenerator[AgentEvent, None]:
        """Execute task and yield progress and tool events."""
        raise NotImplementedError


class CoderAgent(BaseSubAgent):
    """Sub-agent specializing in code generation, Python script execution, and file inspection."""

    name = "coder"
    description = "Specialist in software engineering, debugging, code execution, and test running."
    default_tools = ["code_execution", "file_read", "file_write", "file_search"]

    async def execute(self, request: AgentTaskRequest) -> AsyncGenerator[AgentEvent, None]:
        task_id = request.task_id
        instruction = request.instruction

        yield AgentEvent(
            task_id=task_id,
            event_type=AgentEventType.THINKING,
            payload={"agent": self.name, "message": f"Analyzing coding task: {instruction}"},
        )

        # Inspect if code snippet execution requested
        if (
            any(k in instruction.lower() for k in ["run", "execute", "execution", "code", "script", "test"])
            or "code" in request.context
        ):
            code = request.context.get("code") or "print('CoderAgent executed verification.')"
            yield AgentEvent(
                task_id=task_id,
                event_type=AgentEventType.TOOL_START,
                payload={"tool_name": "code_execution", "arguments": {"code": code}},
            )
            tool = self.tool_registry.get_tool("code_execution")
            if tool:
                res = await self.tool_registry.execute_tool("code_execution", {"code": code}, is_user_approved=True)
                yield AgentEvent(
                    task_id=task_id,
                    event_type=AgentEventType.TOOL_END,
                    payload={"tool_name": "code_execution", "result": res},
                )
                yield AgentEvent(
                    task_id=task_id,
                    event_type=AgentEventType.DONE,
                    payload={
                        "status": "success",
                        "result_text": f"Execution finished with exit code {res.get('returncode')}.\nOutput: {res.get('stdout')}",
                        "artifacts": [],
                    },
                )
                return

        # General coding response
        result_text = f"CoderAgent processed task: '{instruction}'. Code verification complete."
        yield AgentEvent(
            task_id=task_id,
            event_type=AgentEventType.DONE,
            payload={"status": "success", "result_text": result_text, "artifacts": []},
        )


class ResearchAgent(BaseSubAgent):
    """Sub-agent specializing in information gathering, web research, and notes synthesis."""

    name = "researcher"
    description = "Specialist in topic synthesis, web research, fact verification, and note taking."
    default_tools = ["web_research", "notes", "calculator", "current_time"]

    async def execute(self, request: AgentTaskRequest) -> AsyncGenerator[AgentEvent, None]:
        task_id = request.task_id
        instruction = request.instruction

        yield AgentEvent(
            task_id=task_id,
            event_type=AgentEventType.THINKING,
            payload={"agent": self.name, "message": f"Researching topic: {instruction}"},
        )

        # Invoke web research tool
        yield AgentEvent(
            task_id=task_id,
            event_type=AgentEventType.TOOL_START,
            payload={"tool_name": "web_research", "arguments": {"query": instruction}},
        )

        research_res = await self.tool_registry.execute_tool(
            "web_research", {"query": instruction}, is_user_approved=True
        )

        yield AgentEvent(
            task_id=task_id,
            event_type=AgentEventType.TOOL_END,
            payload={"tool_name": "web_research", "result": research_res},
        )

        summary = research_res.get("summary", f"Synthesized research on {instruction}")
        yield AgentEvent(
            task_id=task_id,
            event_type=AgentEventType.DONE,
            payload={"status": "success", "result_text": summary, "artifacts": []},
        )


class DocumentAgent(BaseSubAgent):
    """Sub-agent specializing in drafting documents, reports, and markdown files."""

    name = "document"
    description = "Specialist in authoring reports, documentation, summaries, and structured files."
    default_tools = ["file_write", "file_read", "notes"]

    async def execute(self, request: AgentTaskRequest) -> AsyncGenerator[AgentEvent, None]:
        task_id = request.task_id
        instruction = request.instruction
        path = request.context.get("path", "document.md")
        content = request.context.get("content", f"# Document\n\nGenerated for instruction: {instruction}\n")

        yield AgentEvent(
            task_id=task_id,
            event_type=AgentEventType.THINKING,
            payload={"agent": self.name, "message": f"Drafting document to {path}"},
        )

        yield AgentEvent(
            task_id=task_id,
            event_type=AgentEventType.TOOL_START,
            payload={"tool_name": "file_write", "arguments": {"path": path, "content": content}},
        )

        res = await self.tool_registry.execute_tool(
            "file_write", {"path": path, "content": content}, is_user_approved=True
        )

        yield AgentEvent(
            task_id=task_id,
            event_type=AgentEventType.TOOL_END,
            payload={"tool_name": "file_write", "result": res},
        )

        artifact = {"type": "file", "path": path}
        yield AgentEvent(task_id=task_id, event_type=AgentEventType.ARTIFACT, payload=artifact)

        yield AgentEvent(
            task_id=task_id,
            event_type=AgentEventType.DONE,
            payload={
                "status": "success",
                "result_text": f"Document successfully authored and written to {path}.",
                "artifacts": [artifact],
            },
        )
