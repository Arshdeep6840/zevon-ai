"""Repository for conversations, messages, and settings."""

import json
from datetime import datetime
from typing import List, Optional
import aiosqlite
from packages.shared_schemas.models import Conversation, Message, Role


class MemoryRepository:
    def __init__(self, conn: aiosqlite.Connection):
        self.conn = conn

    async def create_conversation(self, title: str = "New Conversation", profile: str = "personal") -> Conversation:
        conv = Conversation(title=title, profile=profile)
        await self.conn.execute(
            "INSERT INTO conversations (id, title, profile, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (conv.id, conv.title, conv.profile, conv.created_at.isoformat(), conv.updated_at.isoformat()),
        )
        await self.conn.commit()
        return conv

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        cursor = await self.conn.execute(
            "SELECT id, title, profile, created_at, updated_at FROM conversations WHERE id = ?",
            (conversation_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return Conversation(
            id=row["id"],
            title=row["title"],
            profile=row["profile"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    async def list_conversations(self) -> List[Conversation]:
        cursor = await self.conn.execute(
            "SELECT id, title, profile, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
        )
        rows = await cursor.fetchall()
        return [
            Conversation(
                id=r["id"],
                title=r["title"],
                profile=r["profile"],
                created_at=datetime.fromisoformat(r["created_at"]),
                updated_at=datetime.fromisoformat(r["updated_at"]),
            )
            for r in rows
        ]

    async def delete_conversation(self, conversation_id: str) -> bool:
        cursor = await self.conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        await self.conn.commit()
        return cursor.rowcount > 0

    async def update_conversation(
        self, conversation_id: str, title: Optional[str] = None, profile: Optional[str] = None
    ) -> Optional[Conversation]:
        conv = await self.get_conversation(conversation_id)
        if not conv:
            return None
        new_title = title if title is not None else conv.title
        new_profile = profile if profile is not None else conv.profile
        now = datetime.utcnow().isoformat()
        await self.conn.execute(
            "UPDATE conversations SET title = ?, profile = ?, updated_at = ? WHERE id = ?",
            (new_title, new_profile, now, conversation_id),
        )
        await self.conn.commit()
        return await self.get_conversation(conversation_id)

    async def clear_all_conversations(self) -> int:
        cursor = await self.conn.execute("DELETE FROM conversations")
        await self.conn.commit()
        return cursor.rowcount

    async def export_conversation(self, conversation_id: str) -> Optional[dict]:
        conv = await self.get_conversation(conversation_id)
        if not conv:
            return None
        messages = await self.get_messages(conversation_id)
        return {
            "conversation": conv.model_dump(mode="json"),
            "messages": [m.model_dump(mode="json") for m in messages],
        }

    async def add_message(
        self,
        conversation_id: str,
        role: Role,
        content: str,
        tool_calls: Optional[list] = None,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
        )
        tool_calls_json = json.dumps(tool_calls) if tool_calls else None
        await self.conn.execute(
            "INSERT INTO messages (id, conversation_id, role, content, tool_calls, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (msg.id, msg.conversation_id, msg.role.value, msg.content, tool_calls_json, msg.created_at.isoformat()),
        )
        # Update conversation updated_at
        await self.conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), conversation_id),
        )
        await self.conn.commit()
        return msg

    async def get_messages(self, conversation_id: str) -> List[Message]:
        cursor = await self.conn.execute(
            "SELECT id, conversation_id, role, content, tool_calls, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,),
        )
        rows = await cursor.fetchall()
        messages = []
        for r in rows:
            tool_calls = json.loads(r["tool_calls"]) if r["tool_calls"] else None
            messages.append(
                Message(
                    id=r["id"],
                    conversation_id=r["conversation_id"],
                    role=Role(r["role"]),
                    content=r["content"],
                    tool_calls=tool_calls,
                    created_at=datetime.fromisoformat(r["created_at"]),
                )
            )
        return messages

    async def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        cursor = await self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row["value"] if row else default

    async def get_all_settings(self) -> dict:
        cursor = await self.conn.execute("SELECT key, value FROM settings")
        rows = await cursor.fetchall()
        return {r["key"]: r["value"] for r in rows}

    async def set_setting(self, key: str, value: str) -> None:
        await self.conn.execute(
            """
            INSERT INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (key, value),
        )
        await self.conn.commit()
