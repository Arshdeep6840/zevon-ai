"""Agent Dispatcher: Central router for standardized Agent Calling API."""

import logging
from collections.abc import AsyncGenerator
from typing import Any

from packages.agent_protocol.protocol import (
    AgentEvent,
    AgentEventType,
    AgentTaskRequest,
    AgentTaskResponse,
)
from services.agents.registry import (
    BaseSubAgent,
    CoderAgent,
    DocumentAgent,
    ResearchAgent,
)
from services.model_gateway.registry import ModelRegistry
from services.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class AgentDispatcher:
    """Dispatches tasks to specialized sub-agents via standardized Agent Calling API."""

    def __init__(self, tool_registry: ToolRegistry, model_gateway: ModelRegistry | None = None):
        self.tool_registry = tool_registry
        self.model_gateway = model_gateway
        self._agents: dict[str, BaseSubAgent] = {}

        # Register default sub-agents
        self.register_agent(CoderAgent(tool_registry, model_gateway))
        self.register_agent(ResearchAgent(tool_registry, model_gateway))
        self.register_agent(DocumentAgent(tool_registry, model_gateway))

    def register_agent(self, agent: BaseSubAgent) -> None:
        self._agents[agent.name] = agent

    def get_agent(self, name: str) -> BaseSubAgent | None:
        return self._agents.get(name)

    def list_agents(self) -> list[dict[str, Any]]:
        return [
            {
                "name": a.name,
                "description": a.description,
                "default_tools": a.default_tools,
            }
            for a in self._agents.values()
        ]

    async def invoke_stream(self, request: AgentTaskRequest) -> AsyncGenerator[AgentEvent, None]:
        """Stream events during sub-agent execution."""
        agent = self.get_agent(request.target_agent)
        if not agent:
            # Fallback to research agent if unknown
            agent = self._agents.get("researcher")

        if not agent:
            yield AgentEvent(
                task_id=request.task_id,
                event_type=AgentEventType.ERROR,
                payload={"error": f"Agent '{request.target_agent}' not found."},
            )
            return

        async for event in agent.execute(request):
            yield event

    async def invoke(self, request: AgentTaskRequest) -> AgentTaskResponse:
        """Execute sub-agent synchronously and return aggregated response."""
        result_text = ""
        artifacts = []
        status = "success"
        error_msg = None
        total_steps = 0

        async for event in self.invoke_stream(request):
            total_steps += 1
            if event.event_type == AgentEventType.ARTIFACT:
                artifacts.append(event.payload)
            elif event.event_type == AgentEventType.ERROR:
                status = "failed"
                error_msg = event.payload.get("error")
            elif event.event_type == AgentEventType.DONE:
                status = event.payload.get("status", "success")
                result_text = event.payload.get("result_text", "")
                if "artifacts" in event.payload:
                    artifacts.extend(event.payload["artifacts"])

        return AgentTaskResponse(
            task_id=request.task_id,
            agent_name=request.target_agent,
            status=status,
            result_text=result_text,
            artifacts=artifacts,
            total_steps=total_steps,
            error_message=error_msg,
        )
