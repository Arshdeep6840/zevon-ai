"""Test configuration and fixtures for Zevon test suite."""

import os
import pytest
import aiosqlite
from pathlib import Path
from services.memory.database import init_db
from services.memory.repository import MemoryRepository
from services.model_gateway.registry import ModelRegistry


@pytest.fixture
def temp_db_path(tmp_path):
    """Provide a temporary database file path."""
    db_file = tmp_path / "test_zevon.db"
    return str(db_file)


@pytest.fixture
async def memory_repo(temp_db_path):
    """Provide an initialized MemoryRepository fixture."""
    await init_db(temp_db_path)
    async with aiosqlite.connect(temp_db_path) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON;")
        repo = MemoryRepository(conn)
        yield repo


@pytest.fixture
def test_gateway():
    """Provide an offline-enforced ModelRegistry fixture."""
    registry = ModelRegistry(ollama_url="http://localhost:11434")
    registry.set_force_offline(True)
    return registry
