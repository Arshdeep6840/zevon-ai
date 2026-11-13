import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.core.llm import LLMProvider, LLMResponse, ToolCall
from app.main import create_app


class FakeLLM(LLMProvider):
    """Scripted responses so tests need no Ollama."""
    def __init__(self, script):
        self.script = list(script)

    def chat(self, messages, tools=None):
        return self.script.pop(0)


@pytest.fixture
def sandbox(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "pic.png").write_bytes(b"x")
    return tmp_path


def make(sandbox, script):
    cfg = Settings(db_path=":memory:", allowed_folders=[str(sandbox)], vector_memory="off")
    from app.integrations.system import filesystem
    filesystem.settings.allowed_folders = [str(sandbox)]
    return TestClient(create_app(cfg, FakeLLM(script), start_scheduler=False, load_extensions=False))


def test_read_tool_runs_automatically(sandbox):
    c = make(sandbox, [LLMResponse(tool_calls=[ToolCall("fs_list_dir", {"path": str(sandbox)})]),
                       LLMResponse(content="You have a.txt and pic.png")])
    r = c.post("/api/chat", json={"message": "list my files"}).json()
    assert r["steps"][0]["status"] == "ok" and "a.txt" in r["reply"]


def test_delete_requires_approval_then_runs(sandbox):
    target = str(sandbox / "a.txt")
    c = make(sandbox, [LLMResponse(tool_calls=[ToolCall("fs_delete_file", {"path": target})]),
                       LLMResponse(content="Queued.")])
    r = c.post("/api/chat", json={"message": "delete a.txt"}).json()
    assert r["steps"][0]["status"] == "pending_approval"
    assert (sandbox / "a.txt").exists()                       # NOT deleted yet
    pending = c.get("/api/approvals").json()
    assert len(pending) == 1
    c.post(f"/api/approvals/{pending[0]['id']}/approve")
    assert not (sandbox / "a.txt").exists()
    assert any(a["outcome"].startswith("approved") for a in c.get("/api/audit").json())


def test_sandbox_blocks_outside_paths(sandbox):
    c = make(sandbox, [LLMResponse(tool_calls=[ToolCall("fs_read_file", {"path": "/etc/passwd"})]),
                       LLMResponse(content="nope")])
    c.post("/api/chat", json={"message": "read passwd"})
    log = c.get("/api/audit").json()
    assert log  # action was recorded
    from app.integrations.system.filesystem import safe_path
    with pytest.raises(PermissionError):
        safe_path("/etc/passwd")


def test_kill_switch_stops_agent(sandbox):
    c = make(sandbox, [])
    c.post("/api/kill", json={"active": True})
    assert "Kill switch" in c.post("/api/chat", json={"message": "hi"}).json()["reply"]


def test_organize_preview_and_apply(sandbox):
    c = make(sandbox, [LLMResponse(tool_calls=[ToolCall("fs_apply_organize", {"path": str(sandbox)})]),
                       LLMResponse(content="ok")])
    c.post("/api/chat", json={"message": "organize"})
    aid = c.get("/api/approvals").json()[0]["id"]
    c.post(f"/api/approvals/{aid}/approve")
    assert (sandbox / "Images" / "pic.png").exists() and (sandbox / "Documents" / "a.txt").exists()
