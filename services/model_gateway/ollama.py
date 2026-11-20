"""Ollama inference provider for local open-weight models."""

import json
from typing import AsyncIterator, List, Optional, Dict, Any
import httpx
from packages.shared_schemas.models import Message, ModelCard
from .base import BaseModelProvider


class OllamaProvider(BaseModelProvider):
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")

    async def check_health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[ModelCard]:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = []
                    for item in data.get("models", []):
                        name = item.get("name", "unknown")
                        models.append(
                            ModelCard(
                                id=name,
                                name=name,
                                provider="ollama",
                                parameter_size=str(item.get("details", {}).get("parameter_size", "unknown")),
                                quantization=item.get("details", {}).get("quantization_level"),
                                is_installed=True,
                                description=f"Local Ollama model: {name}",
                            )
                        )
                    return models
        except Exception:
            pass
        return []

    async def stream_chat(
        self,
        messages: List[Message],
        model_name: str,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        formatted_messages = [{"role": m.role.value, "content": m.content} for m in messages]
        payload = {
            "model": model_name,
            "messages": formatted_messages,
            "stream": True,
            "options": {"temperature": temperature},
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield f"Error from Ollama ({response.status_code}): {error_text.decode('utf-8', errors='ignore')}"
                    return

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        delta = chunk.get("message", {}).get("content", "")
                        if delta:
                            yield delta
                    except json.JSONDecodeError:
                        continue
