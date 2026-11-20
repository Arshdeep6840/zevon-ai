"""Unit and integration tests for Zevon Core Built-in Tools and Tool Registry."""

from pathlib import Path
import pytest

from services.memory.database import create_connection
from services.memory.repository import MemoryRepository
from services.tools.builtin import (
    AppLaunchTool,
    CalculatorTool,
    CodeExecutionTool,
    FileDeleteTool,
    FileReadTool,
    FileSearchTool,
    FileWriteTool,
    NotesTool,
    SafeMathEvaluator,
    TimeTool,
    WebResearchTool,
)
from services.tools.permissions import (
    ApprovalRequiredError,
    PermissionBroker,
    SecurityViolationError,
)
from services.tools.registry import get_default_tool_registry


@pytest.fixture
def temp_workspace(tmp_path: Path):
    ws = tmp_path / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


@pytest.fixture
def broker(temp_workspace: Path):
    return PermissionBroker(allowed_workspaces=[temp_workspace])


def test_safe_math_evaluator():
    evaluator = SafeMathEvaluator()
    assert evaluator.evaluate("2 + 2") == 4
    assert evaluator.evaluate("10 * 5 - 8 / 2") == 46.0
    assert evaluator.evaluate("2 ** 10") == 1024
    assert evaluator.evaluate("sqrt(144) + abs(-10)") == 22.0
    assert evaluator.evaluate("round(pi, 2)") == 3.14

    with pytest.raises(ZeroDivisionError):
        evaluator.evaluate("10 / 0")

    # Reject dangerous built-ins or variable access
    with pytest.raises(ValueError):
        evaluator.evaluate("__import__('os').system('ls')")

    with pytest.raises(ValueError):
        evaluator.evaluate("open('secret.txt')")


@pytest.mark.asyncio
async def test_calculator_tool(broker: PermissionBroker):
    tool = CalculatorTool()
    res = await tool.execute({"expression": "15 * 3 + 5"}, permission_broker=broker)
    assert res["status"] == "success"
    assert res["result"] == 50


@pytest.mark.asyncio
async def test_time_tool(broker: PermissionBroker):
    tool = TimeTool()
    res = await tool.execute({"timezone": "utc"}, permission_broker=broker)
    assert "iso" in res
    assert res["timezone"] == "UTC"
    assert "unix_timestamp" in res


@pytest.mark.asyncio
async def test_notes_tool(broker: PermissionBroker, temp_db_path: str):
    async def repo_factory():
        conn = await create_connection(temp_db_path)
        return MemoryRepository(conn)

    tool = NotesTool(repository_factory=repo_factory)

    # 1. Create Note (R1)
    create_res = await tool.execute(
        {"action": "create", "title": "Project Idea", "content": "Build voice assistant", "tags": ["ai", "local"]},
        permission_broker=broker,
    )
    assert "id" in create_res
    note_id = create_res["id"]
    assert create_res["title"] == "Project Idea"

    # 2. Read Note (R0)
    read_res = await tool.execute(
        {"action": "read", "note_id": note_id},
        permission_broker=broker,
    )
    assert read_res["id"] == note_id
    assert read_res["content"] == "Build voice assistant"

    # 3. Search Note (R0)
    search_res = await tool.execute(
        {"action": "search", "query": "voice"},
        permission_broker=broker,
    )
    assert len(search_res) >= 1
    assert search_res[0]["id"] == note_id

    # 4. Delete Note requires approval (R2)
    with pytest.raises(ApprovalRequiredError):
        await tool.execute(
            {"action": "delete", "note_id": note_id},
            permission_broker=broker,
            is_user_approved=False,
        )

    # Delete with approval
    del_res = await tool.execute(
        {"action": "delete", "note_id": note_id},
        permission_broker=broker,
        is_user_approved=True,
    )
    assert del_res["deleted"] is True


@pytest.mark.asyncio
async def test_file_tools_lifecycle(broker: PermissionBroker, temp_workspace: Path):
    target_file = temp_workspace / "subfolder" / "test_doc.txt"
    write_tool = FileWriteTool()
    read_tool = FileReadTool()
    search_tool = FileSearchTool()
    delete_tool = FileDeleteTool()

    # 1. Write file
    w_res = await write_tool.execute(
        {"path": str(target_file), "content": "Line 1: Hello Zevon\nLine 2: Local AI Assistant\nLine 3: Privacy first"},
        permission_broker=broker,
    )
    assert w_res["status"] == "success"
    assert target_file.exists()

    # 2. Search files
    s_res = await search_tool.execute(
        {"pattern": "*.txt", "directory": str(temp_workspace)},
        permission_broker=broker,
    )
    assert s_res["count"] >= 1
    assert any("test_doc.txt" in m["path"] for m in s_res["matches"])

    # 3. Read file with line slice
    r_res = await read_tool.execute(
        {"path": str(target_file), "start_line": 1, "end_line": 2},
        permission_broker=broker,
    )
    assert "Line 1: Hello Zevon" in r_res["content"]
    assert "Line 2: Local AI Assistant" in r_res["content"]
    assert "Line 3" not in r_res["content"]

    # 4. Boundary violation check
    outside_file = temp_workspace.parent / "unauthorized.txt"
    with pytest.raises(SecurityViolationError):
        await read_tool.execute({"path": str(outside_file)}, permission_broker=broker)

    # 5. Delete file requires approval (R2)
    with pytest.raises(ApprovalRequiredError):
        await delete_tool.execute(
            {"path": str(target_file)},
            permission_broker=broker,
            is_user_approved=False,
        )

    del_res = await delete_tool.execute(
        {"path": str(target_file)},
        permission_broker=broker,
        is_user_approved=True,
    )
    assert del_res["deleted"] is True
    assert not target_file.exists()


@pytest.mark.asyncio
async def test_code_execution_tool(broker: PermissionBroker):
    tool = CodeExecutionTool()
    res = await tool.execute(
        {"code": "import math\nprint(f'Result: {math.factorial(5)}')"},
        permission_broker=broker,
    )
    assert res["success"] is True
    assert "Result: 120" in res["stdout"]

    # Test timeout bounds
    timeout_res = await tool.execute(
        {"code": "import time\ntime.sleep(5)", "timeout_seconds": 0.5},
        permission_broker=broker,
    )
    assert timeout_res["success"] is False
    assert "timed out" in timeout_res["stderr"].lower()


@pytest.mark.asyncio
async def test_app_launch_and_web_research_tools(broker: PermissionBroker):
    launch_tool = AppLaunchTool()
    # Disallowed app
    with pytest.raises(SecurityViolationError):
        await launch_tool.execute({"app_name": "malicious_binary"}, permission_broker=broker)

    research_tool = WebResearchTool()
    r_res = await research_tool.execute({"query": "Antigravity agents"}, permission_broker=broker)
    assert r_res["status"] == "success"
    assert "Antigravity agents" in r_res["summary"]


@pytest.mark.asyncio
async def test_tool_registry_and_audit(temp_workspace: Path):
    registry = get_default_tool_registry(allowed_workspaces=[temp_workspace])
    schemas = registry.export_schemas()
    assert len(schemas) >= 8

    # Execute calculator through registry
    calc_res = await registry.execute_tool("calculator", {"expression": "99 + 1"})
    assert calc_res["result"] == 100

    # Verify audit log captures tool execution
    audit = registry.permission_broker.audit_log
    assert len(audit) >= 1
    assert audit[-1]["tool_name"] == "calculator"
    assert audit[-1]["approved"] is True
