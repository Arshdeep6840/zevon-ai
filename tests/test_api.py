"""Integration tests for FastAPI endpoints and WebSocket."""

import json

import pytest
from fastapi.testclient import TestClient

from services.api.config import settings
from services.api.main import app
from services.model_gateway.registry import get_model_registry


@pytest.fixture(autouse=True)
def setup_test_database(tmp_path):
    """Ensure a clean temporary database is used for API tests."""
    test_db = str(tmp_path / "api_test.db")
    settings.db_path = test_db
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
