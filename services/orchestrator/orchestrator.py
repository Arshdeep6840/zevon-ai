"""Task Orchestrator & State Machine: Safe execution of multi-step plans with bounded retries and approval gates."""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from packages.agent_protocol.protocol import AgentEvent, AgentEventType
from packages.shared_schemas.models import (
    RiskLevel,
    TaskState,
    TaskStatus,
)
from services.memory.repository import MemoryRepository
from services.orchestrator.planner import TaskPlanner
from services.tools.permissions import ApprovalRequiredError
from services.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class TaskOrchestrator:
    """
    Coordinates multi-step task execution, enforcing:
    1. Task state machine transitions.
    2. Human-in-the-loop approval gates for Risk Level R2 & R3 steps.
    3. Bounded retries (max 3) for transient step failures.
    4. Cancellation support at any point during execution.
    5. Real-time event streaming for UI subscribers.
    """

    MAX_RETRIES = 3

    def __init__(
        self,
        tool_registry: ToolRegistry,
        planner: TaskPlanner,
        repository_factory=None,
    ):
        self.tool_registry = tool_registry
        self.planner = planner
        self.repository_factory = repository_factory
        self._active_tasks: dict[str, TaskState] = {}
        self._approved_steps: dict[str, set[int]] = {}  # task_id -> set of step_ids
        self._event_subscribers: dict[str, list[asyncio.Queue[AgentEvent]]] = {}
        self._cancellation_flags: dict[str, bool] = {}

    def subscribe(self, task_id: str) -> asyncio.Queue[AgentEvent]:
        """Subscribe to live execution events for a task."""
        queue: asyncio.Queue[AgentEvent] = asyncio.Queue()
        if task_id not in self._event_subscribers:
            self._event_subscribers[task_id] = []
        self._event_subscribers[task_id].append(queue)
        return queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue[AgentEvent]) -> None:
        """Unsubscribe from task event notifications."""
        if task_id in self._event_subscribers:
            if queue in self._event_subscribers[task_id]:
                self._event_subscribers[task_id].remove(queue)
            if not self._event_subscribers[task_id]:
                del self._event_subscribers[task_id]

    async def emit_event(self, task_id: str, event_type: AgentEventType, payload: dict[str, Any]) -> None:
        """Broadcast an event to all task subscribers."""
        event = AgentEvent(task_id=task_id, event_type=event_type, payload=payload)
        subscribers = self._event_subscribers.get(task_id, [])
        for q in subscribers:
            await q.put(event)

    async def stream_events(self, task_id: str) -> AsyncGenerator[str, None]:
        """Yield SSE-formatted event stream for a given task."""
        q = self.subscribe(task_id)
        try:
            while True:
                event = await q.get()
                yield f"data: {event.model_dump_json()}\n\n"
                if event.event_type in (AgentEventType.DONE, AgentEventType.ERROR):
                    break
        finally:
            self.unsubscribe(task_id, q)

    async def _get_repo(self) -> MemoryRepository | None:
        if self.repository_factory:
            return await self.repository_factory()
        return None

    async def create_task(self, prompt: str, conversation_id: str = "default") -> TaskState:
        """Create a new task in PENDING state."""
        task = TaskState(
            conversation_id=conversation_id,
            status=TaskStatus.PENDING,
            prompt=prompt,
        )
        self._active_tasks[task.id] = task
        self._approved_steps[task.id] = set()
        self._cancellation_flags[task.id] = False

        repo = await self._get_repo()
        if repo:
            await repo.create_task(task)

        return task

    async def get_task(self, task_id: str) -> TaskState | None:
        """Get task by ID from memory cache or database."""
        if task_id in self._active_tasks:
            return self._active_tasks[task_id]
        repo = await self._get_repo()
        if repo:
            task = await repo.get_task(task_id)
            if task:
                self._active_tasks[task.id] = task
                return task
        return None

    async def list_tasks(self, conversation_id: str | None = None) -> list[TaskState]:
        """List tasks, merging in-memory state with database."""
        repo = await self._get_repo()
        if repo:
            db_tasks = await repo.list_tasks(conversation_id)
            # Update memory cache
            for t in db_tasks:
                if t.id not in self._active_tasks:
                    self._active_tasks[t.id] = t
        if conversation_id:
            return [t for t in self._active_tasks.values() if t.conversation_id == conversation_id]
        return list(self._active_tasks.values())

    async def cancel_task(self, task_id: str) -> TaskState:
        """Cancel an ongoing or pending task."""
        task = await self.get_task(task_id)
        if not task:
            raise KeyError(f"Task with ID '{task_id}' not found.")

        self._cancellation_flags[task_id] = True
        task.status = TaskStatus.CANCELLED
        task.updated_at = datetime.now(UTC)

        repo = await self._get_repo()
        if repo:
            await repo.update_task(task)

        await self.emit_event(
            task_id,
            AgentEventType.DONE,
            {"status": "cancelled", "message": "Task cancelled by user."},
        )
        return task

    async def approve_step(self, task_id: str, step_id: int, approved: bool, reason: str | None = None) -> TaskState:
        """Handle human-in-the-loop decision for a pending R2/R3 step."""
        task = await self.get_task(task_id)
        if not task:
            raise KeyError(f"Task with ID '{task_id}' not found.")

        if task.status != TaskStatus.WAITING_APPROVAL:
            raise ValueError(f"Task '{task_id}' is in state '{task.status}', not waiting for approval.")

        if not approved:
            # Rejection stops execution
            for step in task.plan:
                if step.step_id == step_id:
                    step.status = "rejected"
                    step.result = f"Rejected by user: {reason or 'No reason provided'}"
            task.status = TaskStatus.CANCELLED
            task.updated_at = datetime.now(UTC)

            repo = await self._get_repo()
            if repo:
                await repo.update_task(task)

            await self.emit_event(
                task_id,
                AgentEventType.DONE,
                {"status": "cancelled", "message": f"Step {step_id} rejected by user."},
            )
            return task

        # Approval granted
        if task_id not in self._approved_steps:
            self._approved_steps[task_id] = set()
        self._approved_steps[task_id].add(step_id)

        # Resume execution
        asyncio.create_task(self._execute_plan(task))
        return task

    async def run_task(self, task_id: str) -> TaskState:
        """Start task planning and execution asynchronously."""
        task = await self.get_task(task_id)
        if not task:
            raise KeyError(f"Task with ID '{task_id}' not found.")

        # Step 1: Planning
        task.status = TaskStatus.PLANNING
        await self.emit_event(task_id, AgentEventType.THINKING, {"message": "Decomposing request into plan steps..."})

        plan = await self.planner.plan(task.prompt)
        task.plan = plan
        task.status = TaskStatus.RUNNING
        task.updated_at = datetime.now(UTC)

        repo = await self._get_repo()
        if repo:
            await repo.update_task(task)

        await self.emit_event(
            task_id,
            AgentEventType.PROGRESS,
            {"message": "Plan generated.", "steps": [s.model_dump() for s in plan]},
        )

        # Step 2: Execution
        asyncio.create_task(self._execute_plan(task))
        return task

    async def _execute_plan(self, task: TaskState) -> None:
        """Iterate through plan steps until completion, failure, cancellation, or approval gate."""
        repo = await self._get_repo()
        task_id = task.id
        context = {"task_id": task_id, "repository": repo}

        task.status = TaskStatus.RUNNING
        if repo:
            await repo.update_task(task)

        while task.current_step < len(task.plan):
            if self._cancellation_flags.get(task_id, False):
                task.status = TaskStatus.CANCELLED
                if repo:
                    await repo.update_task(task)
                return

            step = task.plan[task.current_step]
            step_id = step.step_id
            is_approved = step_id in self._approved_steps.get(task_id, set())

            # Check Risk Level gate
            if step.risk_level in (RiskLevel.R2, RiskLevel.R3) and not is_approved:
                step.status = "waiting_approval"
                task.status = TaskStatus.WAITING_APPROVAL
                task.updated_at = datetime.now(UTC)
                if repo:
                    await repo.update_task(task)

                await self.emit_event(
                    task_id,
                    AgentEventType.PROGRESS,
                    {
                        "status": "waiting_approval",
                        "step_id": step_id,
                        "title": step.title,
                        "risk_level": step.risk_level.value,
                        "tool_name": step.tool_name,
                        "arguments": step.arguments,
                    },
                )
                return  # Halts loop until approve_step is called

            # Execute Step with Bounded Retries
            step.status = "running"
            await self.emit_event(
                task_id,
                AgentEventType.TOOL_START,
                {"step_id": step_id, "title": step.title, "tool_name": step.tool_name, "arguments": step.arguments},
            )

            success = False
            last_error = ""

            for attempt in range(1, self.MAX_RETRIES + 1):
                try:
                    if step.tool_name:
                        res = await self.tool_registry.execute_tool(
                            step.tool_name,
                            step.arguments,
                            is_user_approved=is_approved,
                            context=context,
                        )
                        step.result = json.dumps(res) if not isinstance(res, str) else res

                        # Capture artifacts if created
                        if isinstance(res, dict):
                            if "path" in res and res.get("status") == "success":
                                artifact = {"type": "file", "path": res["path"], "action": res.get("action", "written")}
                                task.artifacts.append(artifact)
                                await self.emit_event(task_id, AgentEventType.ARTIFACT, artifact)
                            elif "note_id" in res:
                                artifact = {"type": "note", "note_id": res["note_id"], "title": res.get("title")}
                                task.artifacts.append(artifact)
                                await self.emit_event(task_id, AgentEventType.ARTIFACT, artifact)
                    else:
                        step.result = f"Completed synthetic step: {step.title}"

                    step.status = "completed"
                    success = True
                    break
                except ApprovalRequiredError:
                    # Encountered dynamic approval requirement
                    step.status = "waiting_approval"
                    task.status = TaskStatus.WAITING_APPROVAL
                    if repo:
                        await repo.update_task(task)
                    await self.emit_event(task_id, AgentEventType.PROGRESS, {"status": "waiting_approval", "step_id": step_id})
                    return
                except Exception as e:
                    last_error = str(e)
                    logger.warning("Step %s failed attempt %s/%s: %s", step_id, attempt, self.MAX_RETRIES, e)
                    if attempt < self.MAX_RETRIES:
                        await asyncio.sleep(0.5 * attempt)

            if not success:
                step.status = "failed"
                step.result = f"Failed after {self.MAX_RETRIES} attempts: {last_error}"
                task.status = TaskStatus.FAILED
                task.updated_at = datetime.now(UTC)
                if repo:
                    await repo.update_task(task)
                await self.emit_event(
                    task_id,
                    AgentEventType.ERROR,
                    {"step_id": step_id, "error": step.result},
                )
                return

            await self.emit_event(
                task_id,
                AgentEventType.TOOL_END,
                {"step_id": step_id, "result": step.result},
            )

            task.current_step += 1
            task.updated_at = datetime.now(UTC)
            if repo:
                await repo.update_task(task)

        # All steps completed successfully
        task.status = TaskStatus.COMPLETED
        task.updated_at = datetime.now(UTC)
        if repo:
            await repo.update_task(task)

        await self.emit_event(
            task_id,
            AgentEventType.DONE,
            {
                "status": "completed",
                "total_steps": len(task.plan),
                "artifacts": task.artifacts,
            },
        )
