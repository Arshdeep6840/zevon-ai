"""Integration tests for FastAPI endpoints and WebSocket."""

import json

import pytest
from fastapi.testclient import TestClient

from services.api.config import settings
import services.api.dependencies as deps
from services.api.main import app
from services.model_gateway.registry import get_model_registry


@pytest.fixture(autouse=True)
def setup_test_database(tmp_path):
    """Ensure a clean temporary database is used for API tests."""
    test_db = str(tmp_path / "api_test.db")
    settings.db_path = test_db
    deps._tool_registry = None
    deps._orchestrator = None
    deps._mcp_manager = None
    deps._zevon_mcp_server = None
    deps._agent_dispatcher = None
    get_model_registry().set_force_offline(True)
    get_model_registry().set_active_model("zevon-offline-compact")


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "version" in data
    assert "model_runtime" in data


def test_models_endpoints(client):
    # List models
    res = client.get("/api/v1/models")
    assert res.status_code == 200
    models = res.json()
    assert len(models) >= 1

    # Active model
    res_active = client.get("/api/v1/models/active")
    assert res_active.status_code == 200
    active = res_active.json()
    assert "id" in active

    # Hardware profile
    res_hw = client.get("/api/v1/models/hardware")
    assert res_hw.status_code == 200
    hw = res_hw.json()
    assert "ram_gb" in hw


def test_profiles_and_settings(client):
    # Profiles list
    res_p = client.get("/api/v1/profiles")
    assert res_p.status_code == 200
    profiles = res_p.json()
    assert len(profiles) == 4
    ids = [p["id"] for p in profiles]
    assert "personal" in ids
    assert "developer" in ids
    assert "business" in ids
    assert "creator" in ids

    # Settings
    res_s = client.get("/api/v1/settings")
    assert res_s.status_code == 200

    # Update setting
    res_update = client.post("/api/v1/settings", json={"settings": {"theme": "emerald"}})
    assert res_update.status_code == 200


def test_conversation_crud_and_export(client):
    # Create
    res = client.post("/api/v1/conversations", json={"title": "Test Chat", "profile": "developer"})
    assert res.status_code == 200
    conv = res.json()
    conv_id = conv["id"]

    # List
    res_list = client.get("/api/v1/conversations")
    assert res_list.status_code == 200
    assert any(c["id"] == conv_id for c in res_list.json())

    # Get single
    res_get = client.get(f"/api/v1/conversations/{conv_id}")
    assert res_get.status_code == 200
    assert res_get.json()["conversation"]["id"] == conv_id

    # Patch
    res_patch = client.patch(f"/api/v1/conversations/{conv_id}", json={"title": "Renamed Chat"})
    assert res_patch.status_code == 200
    assert res_patch.json()["title"] == "Renamed Chat"

    # Export
    res_exp = client.get(f"/api/v1/conversations/{conv_id}/export?format=markdown")
    assert res_exp.status_code == 200
    assert "markdown" in res_exp.json()

    # Delete
    res_del = client.delete(f"/api/v1/conversations/{conv_id}")
    assert res_del.status_code == 200


def test_chat_non_streaming(client):
    payload = {
        "message": "Who are you?",
        "stream": False,
        "temperature": 0.7,
    }
    res = client.post("/api/v1/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "conversation_id" in data
    assert "content" in data
    assert "Zevon" in data["content"]


def test_chat_streaming_sse(client):
    payload = {
        "message": "What time is it?",
        "stream": True,
        "temperature": 0.7,
    }
    res = client.post("/api/v1/chat", json=payload)
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]
    body = res.text
    assert "data: " in body
    assert "finish_reason" in body


def test_realtime_websocket(client):
    with client.websocket_connect("/api/v1/realtime") as ws:
        # Test ping/pong
        ws.send_text(json.dumps({"type": "ping"}))
        pong = json.loads(ws.receive_text())
        assert pong.get("type") == "pong"

        # Test chat streaming
        ws.send_text(
            json.dumps(
                {
                    "type": "chat",
                    "message": "Who are you?",
                }
            )
        )

        received_types = []
        for _ in range(60):
            msg = json.loads(ws.receive_text())
            received_types.append(msg.get("type"))
            if msg.get("type") in ["done", "error"]:
                break

        assert "start" in received_types
        assert "delta" in received_types
        assert "done" in received_types


def test_tools_api(client):
    # List tools
    res = client.get("/api/v1/tools")
    assert res.status_code == 200
    tools = res.json()
    assert len(tools) >= 8
    names = [t["name"] for t in tools]
    assert "calculator" in names
    assert "current_time" in names

    # Execute R0 tool
    res_exec = client.post("/api/v1/tools/execute", json={"name": "calculator", "arguments": {"expression": "12 * 12"}})
    assert res_exec.status_code == 200
    assert res_exec.json()["result"]["result"] == 144

    # Audit trail
    res_audit = client.get("/api/v1/tools/audit")
    assert res_audit.status_code == 200
    assert len(res_audit.json()) >= 1


def test_tasks_api(client):
    # Create task
    res = client.post("/api/v1/tasks", json={"prompt": "Calculate 40 + 2"})
    assert res.status_code == 200
    task = res.json()
    task_id = task["id"]
    assert task["status"] in ["pending", "planning", "running", "completed"]

    # Get task
    res_get = client.get(f"/api/v1/tasks/{task_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == task_id

    # List tasks
    res_list = client.get("/api/v1/tasks")
    assert res_list.status_code == 200
    assert any(t["id"] == task_id for t in res_list.json())

    # Cancel task
    res_cancel = client.post(f"/api/v1/tasks/{task_id}/cancel")
    assert res_cancel.status_code == 200


def test_mcp_api(client):
    # List MCP servers
    res = client.get("/api/v1/mcp/servers")
    assert res.status_code == 200

    # Zevon MCP Messages endpoint
    res_msg = client.post(
        "/api/v1/mcp/messages",
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    )
    assert res_msg.status_code == 200
    assert res_msg.json()["result"]["serverInfo"]["name"] == "zevon-mcp-server"


def test_agents_api(client):
    # List agents
    res = client.get("/api/v1/agents")
    assert res.status_code == 200
    agents = res.json()
    names = [a["name"] for a in agents]
    assert "coder" in names
    assert "researcher" in names

    # Invoke agent non-streaming
    res_invoke = client.post(
        "/api/v1/agents/invoke",
        json={
            "target_agent": "researcher",
            "instruction": "Test agent dispatch",
            "stream_events": False,
        },
    )
    assert res_invoke.status_code == 200
    data = res_invoke.json()
    assert data["status"] == "success"
    assert "Test agent dispatch" in data["result_text"]
