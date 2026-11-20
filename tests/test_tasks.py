"""Unit and integration tests for Task Planner and Task Orchestrator."""

import asyncio
from pathlib import Path
import pytest

from packages.shared_schemas.models import RiskLevel, TaskStatus
from services.memory.database import create_connection
from services.memory.repository import MemoryRepository
from services.orchestrator.orchestrator import TaskOrchestrator
from services.orchestrator.planner import TaskPlanner
from services.tools.registry import get_default_tool_registry


@pytest.fixture
def temp_workspace(tmp_path: Path):
    ws = tmp_path / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


@pytest.fixture
def orchestrator(temp_workspace: Path, temp_db_path: str):
    tools = get_default_tool_registry(allowed_workspaces=[temp_workspace])
    planner = TaskPlanner(tool_registry=tools)

    async def repo_factory():
        conn = await create_connection(temp_db_path)
        return MemoryRepository(conn)

    return TaskOrchestrator(
        tool_registry=tools,
        planner=planner,
        repository_factory=repo_factory,
    )


@pytest.mark.asyncio
async def test_task_planner_heuristics(temp_workspace: Path):
    tools = get_default_tool_registry(allowed_workspaces=[temp_workspace])
    planner = TaskPlanner(tool_registry=tools)

    # 1. Single-step math
    plan1 = await planner.plan("calculate 128 * 8")
    assert len(plan1) == 1
    assert plan1[0].tool_name == "calculator"
    assert plan1[0].risk_level == RiskLevel.R0

    # 2. Multi-step: calculate and write to file
    plan2 = await planner.plan("Calculate 25 * 4 and write to totals.txt")
    assert len(plan2) == 2
    assert plan2[0].tool_name == "calculator"
    assert plan2[1].tool_name == "file_write"
    assert plan2[1].risk_level == RiskLevel.R1

    # 3. Destructive action (R2)
    plan3 = await planner.plan("delete file obsolete.txt")
    assert len(plan3) == 1
    assert plan3[0].tool_name == "file_delete"
    assert plan3[0].risk_level == RiskLevel.R2


@pytest.mark.asyncio
async def test_orchestrator_auto_execution(orchestrator: TaskOrchestrator):
    task = await orchestrator.create_task("Calculate 100 * 5")
    assert task.status == TaskStatus.PENDING

    # Run task
    await orchestrator.run_task(task.id)

    # Allow async execution loop to complete
    for _ in range(20):
        await asyncio.sleep(0.1)
        updated = await orchestrator.get_task(task.id)
        if updated and updated.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            break

    final_task = await orchestrator.get_task(task.id)
    assert final_task is not None
    assert final_task.status == TaskStatus.COMPLETED
    assert len(final_task.plan) == 1
    assert final_task.plan[0].status == "completed"
    assert "500" in (final_task.plan[0].result or "")


@pytest.mark.asyncio
async def test_orchestrator_r2_approval_gate(orchestrator: TaskOrchestrator, temp_workspace: Path):
    # Create file first so delete can succeed
    target = temp_workspace / "old_log.txt"
    target.write_text("Old log data", encoding="utf-8")

    task = await orchestrator.create_task(f"delete file {target}")
    await orchestrator.run_task(task.id)

    # Wait until task hits approval gate
    for _ in range(20):
        await asyncio.sleep(0.1)
        t = await orchestrator.get_task(task.id)
        if t and t.status == TaskStatus.WAITING_APPROVAL:
            break

    gate_task = await orchestrator.get_task(task.id)
    assert gate_task is not None
    assert gate_task.status == TaskStatus.WAITING_APPROVAL
    assert gate_task.plan[0].status == "waiting_approval"
    assert gate_task.plan[0].risk_level == RiskLevel.R2
    assert target.exists()  # Not deleted yet!

    # Human approves the action
    await orchestrator.approve_step(task.id, step_id=1, approved=True)

    # Wait for completion
    for _ in range(20):
        await asyncio.sleep(0.1)
        t = await orchestrator.get_task(task.id)
        if t and t.status == TaskStatus.COMPLETED:
            break

    completed_task = await orchestrator.get_task(task.id)
    assert completed_task is not None
    assert completed_task.status == TaskStatus.COMPLETED
    assert not target.exists()  # File successfully deleted!


@pytest.mark.asyncio
async def test_orchestrator_rejection_flow(orchestrator: TaskOrchestrator, temp_workspace: Path):
    target = temp_workspace / "important_file.txt"
    target.write_text("Critical data", encoding="utf-8")

    task = await orchestrator.create_task(f"delete file {target}")
    await orchestrator.run_task(task.id)

    # Wait for WAITING_APPROVAL
    for _ in range(20):
        await asyncio.sleep(0.1)
        t = await orchestrator.get_task(task.id)
        if t and t.status == TaskStatus.WAITING_APPROVAL:
            break

    # User explicitly rejects the deletion
    await orchestrator.approve_step(task.id, step_id=1, approved=False, reason="Safety check failed")

    rejected_task = await orchestrator.get_task(task.id)
    assert rejected_task is not None
    assert rejected_task.status == TaskStatus.CANCELLED
    assert target.exists()  # Protected!


@pytest.mark.asyncio
async def test_orchestrator_cancellation(orchestrator: TaskOrchestrator):
    task = await orchestrator.create_task("Calculate 1 + 1")
    cancelled = await orchestrator.cancel_task(task.id)
    assert cancelled.status == TaskStatus.CANCELLED
