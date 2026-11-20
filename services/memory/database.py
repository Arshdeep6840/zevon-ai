"""Async SQLite database manager for Zevon."""

import os
from pathlib import Path
from typing import AsyncGenerator, Optional
import aiosqlite

DEFAULT_DB_PATH = os.getenv("ZEVON_DB_PATH", "zevon.db")
_initialized_dbs = set()


async def init_db(db_path: Optional[str] = None) -> None:
    """Initialize SQLite schema for local persistence."""
    path = db_path or os.getenv("ZEVON_DB_PATH", DEFAULT_DB_PATH)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(path) as conn:
        await conn.execute("PRAGMA foreign_keys = ON;")

        # Conversations table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                profile TEXT NOT NULL DEFAULT 'personal',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Messages table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_calls TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
            );
        """)

        # Settings table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Tasks table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                status TEXT NOT NULL,
                prompt TEXT NOT NULL,
                plan TEXT NOT NULL,
                current_step INTEGER DEFAULT 0,
                artifacts TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
            );
        """)

        await conn.commit()
    _initialized_dbs.add(str(path))


async def get_db(db_path: Optional[str] = None) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Yield an async database connection, ensuring schema exists."""
    path = str(db_path or os.getenv("ZEVON_DB_PATH", DEFAULT_DB_PATH))
    if path not in _initialized_dbs:
        await init_db(path)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(path) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
