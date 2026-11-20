"""Base interface for model inference providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from packages.shared_schemas.models import Message, ModelCard


class BaseModelProvider(ABC):
    """Abstract interface isolating LLM backends (Ollama, llama.cpp, vLLM, mock)."""

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[Message],
        model_name: str,
        temperature: float = 0.7,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]:
        """Stream response tokens asynchronously."""

    @abstractmethod
    async def list_models(self) -> list[ModelCard]:
        """List available models supported by this provider."""

    @abstractmethod
    async def check_health(self) -> bool:
        """Check whether the inference backend is reachable and ready."""
