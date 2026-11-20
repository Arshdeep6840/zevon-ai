"""Async SQLite database manager for Zevon."""

import os
from pathlib import Path
from typing import AsyncGenerator, Optional, Tuple

import aiosqlite  # type: ignore[missing-import]

DEFAULT_DB_PATH = os.getenv("ZEVON_DB_PATH", "zevon.db")
_initialized_dbs = set()


def resolve_sqlite_target(path: str) -> Tuple[str, bool]:
    """
    Resolve SQLite connection target.
    Handles Windows UNC paths (e.g. \\\\wsl.localhost\\...) by using URI mode with nolock=1
    to avoid 'database is locked' errors over 9P/SMB network mounts.
    """
    p = Path(path)
    try:
        p_str = str(p.resolve())
    except Exception:
        p_str = str(p)

    if p_str.startswith("\\\\"):
        normalized = p_str.lstrip("\\").replace("\\", "/")
        return f"file:////{normalized}?nolock=1", True
    return p_str, False


async def init_db(db_path: Optional[str] = None) -> None:
    """Initialize SQLite schema for local persistence."""
    raw_path = db_path or os.getenv("ZEVON_DB_PATH", DEFAULT_DB_PATH)
    target, is_uri = resolve_sqlite_target(raw_path)
    Path(raw_path).parent.mkdir(parents=True, exist_ok=True)

    connect_kwargs = {"timeout": 30.0}
    if is_uri:
        connect_kwargs["uri"] = True

    async with aiosqlite.connect(target, **connect_kwargs) as conn:
        await conn.execute("PRAGMA busy_timeout = 5000;")
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
    _initialized_dbs.add(str(raw_path))


async def get_db(db_path: Optional[str] = None) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Yield an async database connection, ensuring schema exists."""
    raw_path = str(db_path or os.getenv("ZEVON_DB_PATH", DEFAULT_DB_PATH))
    if raw_path not in _initialized_dbs:
        await init_db(raw_path)
    target, is_uri = resolve_sqlite_target(raw_path)
    Path(raw_path).parent.mkdir(parents=True, exist_ok=True)

    connect_kwargs = {"timeout": 30.0}
    if is_uri:
        connect_kwargs["uri"] = True

    async with aiosqlite.connect(target, **connect_kwargs) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA busy_timeout = 5000;")
        await conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
