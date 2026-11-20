"""Agent Calling API endpoints for sub-agent invocation."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from packages.agent_protocol.protocol import (
    AgentTaskRequest,
    AgentTaskResponse,
)
from services.agents.dispatcher import AgentDispatcher
from services.api.dependencies import get_agent_dispatcher

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.get("")
async def list_agents(
    dispatcher: AgentDispatcher = Depends(get_agent_dispatcher),
):
    """List available specialized sub-agents and their default toolsets."""
    return dispatcher.list_agents()


@router.post("/invoke", response_model=None)
async def invoke_agent(
    req: AgentTaskRequest,
    dispatcher: AgentDispatcher = Depends(get_agent_dispatcher),
):
    """Invoke a specialized sub-agent via standardized Agent Calling API."""
    if not req.instruction.strip():
        raise HTTPException(status_code=400, detail="Instruction must not be empty.")

    if req.stream_events:
        async def event_generator():
            async for event in dispatcher.invoke_stream(req):
                yield f"data: {event.model_dump_json()}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    response: AgentTaskResponse = await dispatcher.invoke(req)
    return response
