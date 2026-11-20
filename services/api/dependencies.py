"""FastAPI dependency injection providers."""

from collections.abc import AsyncGenerator

from services.api.config import settings
from services.memory.database import get_db
from services.memory.repository import MemoryRepository
from services.model_gateway.registry import ModelRegistry, get_model_registry


async def get_repository() -> AsyncGenerator[MemoryRepository, None]:
    """Provide a MemoryRepository backed by an async database connection."""
    async for conn in get_db(settings.db_path):
        yield MemoryRepository(conn)


def get_gateway() -> ModelRegistry:
    """Provide the global ModelRegistry instance."""
    return get_model_registry(ollama_url=settings.ollama_url)
