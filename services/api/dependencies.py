"""FastAPI dependency injection providers."""

from typing import AsyncGenerator
import aiosqlite
from services.memory.database import get_db
from services.memory.repository import MemoryRepository
from services.model_gateway.registry import get_model_registry, ModelRegistry
from services.api.config import settings


async def get_repository() -> AsyncGenerator[MemoryRepository, None]:
    """Provide a MemoryRepository backed by an async database connection."""
    async for conn in get_db():
        yield MemoryRepository(conn)


def get_gateway() -> ModelRegistry:
    """Provide the global ModelRegistry instance."""
    return get_model_registry(ollama_url=settings.ollama_url)
