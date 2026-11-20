"""Base interface for model inference providers."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Optional, Dict, Any
from packages.shared_schemas.models import Message, ModelCard


class BaseModelProvider(ABC):
    """Abstract interface isolating LLM backends (Ollama, llama.cpp, vLLM, mock)."""

    @abstractmethod
    async def stream_chat(
        self,
        messages: List[Message],
        model_name: str,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """Stream response tokens asynchronously."""
        pass

    @abstractmethod
    async def list_models(self) -> List[ModelCard]:
        """List available models supported by this provider."""
        pass

    @abstractmethod
    async def check_health(self) -> bool:
        """Check whether the inference backend is reachable and ready."""
        pass
