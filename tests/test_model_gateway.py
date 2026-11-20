"""Unit tests for model gateway, hardware profiling, and offline mock provider."""

import pytest

from packages.shared_schemas.models import Message, ModelCard, Role
from services.model_gateway.offline_mock import OfflineMockProvider
from services.model_gateway.ollama import OllamaProvider
from services.model_gateway.registry import HardwareProfile, ModelRegistry


@pytest.mark.asyncio
async def test_ollama_provider_parsing_and_filtering():
    from unittest.mock import AsyncMock, patch

    provider = OllamaProvider(base_url="http://mock-ollama:11434")
    mock_tags = {
        "models": [
            {
                "name": "nomic-embed-text:latest",
                "capabilities": ["embedding"],
                "details": {"family": "nomic-bert", "parameter_size": "137M"},
            },
            {
                "name": "qwen3:1.7b",
                "capabilities": ["completion", "tools"],
                "details": {
                    "family": "qwen3",
                    "parameter_size": "2.0B",
                    "quantization_level": "Q4_K_M",
                },
            },
        ]
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.json = lambda: mock_tags
        mock_get.return_value = mock_resp

        models = await provider.list_models()
        assert len(models) == 1
        assert models[0].id == "qwen3:1.7b"
        assert models[0].provider == "ollama"
        assert models[0].parameter_size == "2.0B"


@pytest.mark.asyncio
async def test_offline_mock_provider():
    mock = OfflineMockProvider()
    assert await mock.check_health() is True

    models = await mock.list_models()
    assert len(models) >= 2
    assert any(m.id == "zevon-offline-compact" for m in models)

    # Test identity stream
    messages = [Message(conversation_id="c1", role=Role.USER, content="Who are you?")]
    chunks = []
    async for chunk in mock.stream_chat(messages, "zevon-offline-compact"):
        chunks.append(chunk)

    full_text = "".join(chunks)
    assert "Zevon" in full_text
    assert "local-first" in full_text.lower()


@pytest.mark.asyncio
async def test_hardware_profiler():
    hw = HardwareProfile.get_hardware_info()
    assert "ram_gb" in hw
    assert "cpu_cores" in hw
    assert "tier" in hw
    assert hw["tier"] in ["compact", "balanced", "performance"]

    # Test model fit ratings
    compact_model = ModelCard(id="test-1b", name="Test 1B", provider="mock", parameter_size="1B")
    assert HardwareProfile.assess_model_fit(compact_model, 8.0) == "optimal"

    heavy_model = ModelCard(id="test-70b", name="Test 70B", provider="mock", parameter_size="70B")
    assert HardwareProfile.assess_model_fit(heavy_model, 16.0) == "heavy"


@pytest.mark.asyncio
async def test_model_registry_offline_mode():
    registry = ModelRegistry()
    registry.set_force_offline(True)

    models = await registry.list_models()
    assert len(models) >= 1
    assert all(m.provider == "offline-embedded" for m in models)

    active = await registry.get_active_model()
    assert active is not None
    assert active.provider == "offline-embedded"

    # Health check
    health = await registry.check_health()
    assert health["status"] == "ok"
    assert health["mode"] == "offline"
    assert health["force_offline"] is True

    # Streaming through registry
    messages = [Message(conversation_id="c1", role=Role.USER, content="What is MCP?")]
    chunks = []
    async for chunk in registry.stream_chat(messages):
        chunks.append(chunk)

    full_text = "".join(chunks)
    assert "Model Context Protocol" in full_text
