"""Task Orchestration and Execution API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from packages.shared_schemas.models import ApprovalRequest, TaskState
from services.api.dependencies import get_orchestrator
from services.orchestrator.orchestrator import TaskOrchestrator

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


class CreateTaskRequest(BaseModel):
    prompt: str
    conversation_id: str = "default"


@router.post("", response_model=TaskState)
async def create_task(
    req: CreateTaskRequest,
    orchestrator: TaskOrchestrator = Depends(get_orchestrator),
):
    """Create and trigger multi-step execution of an agent task."""
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt must not be empty.")

    task = await orchestrator.create_task(
        prompt=req.prompt,
        conversation_id=req.conversation_id,
    )
    # Trigger background planning and execution
    await orchestrator.run_task(task.id)
    return task


@router.get("", response_model=list[TaskState])
async def list_tasks(
    conversation_id: str | None = Query(None),
    orchestrator: TaskOrchestrator = Depends(get_orchestrator),
):
    """List all tasks, optionally filtered by conversation."""
    return await orchestrator.list_tasks(conversation_id)


@router.get("/{task_id}", response_model=TaskState)
async def get_task(
    task_id: str,
    orchestrator: TaskOrchestrator = Depends(get_orchestrator),
):
    """Retrieve details, execution plan, and status of a specific task."""
    task = await orchestrator.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    return task


@router.post("/{task_id}/approve", response_model=TaskState)
async def approve_step(
    task_id: str,
    req: ApprovalRequest,
    orchestrator: TaskOrchestrator = Depends(get_orchestrator),
):
    """Approve or reject a pending R2/R3 execution step."""
    try:
        return await orchestrator.approve_step(
            task_id=task_id,
            step_id=req.step_id,
            approved=req.approved,
            reason=req.reason,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{task_id}/cancel", response_model=TaskState)
async def cancel_task(
    task_id: str,
    orchestrator: TaskOrchestrator = Depends(get_orchestrator),
):
    """Cancel an active or pending task."""
    try:
        return await orchestrator.cancel_task(task_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{task_id}/events")
async def stream_task_events(
    task_id: str,
    orchestrator: TaskOrchestrator = Depends(get_orchestrator),
):
    """Subscribe to real-time Server-Sent Events (SSE) for task execution progress."""
    task = await orchestrator.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    return StreamingResponse(
        orchestrator.stream_events(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
