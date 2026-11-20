"""Repository for conversations, messages, and settings."""

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import aiosqlite

from packages.shared_schemas.models import (
    Conversation,
    Message,
    Role,
    TaskPlanStep,
    TaskState,
    TaskStatus,
)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class MemoryRepository:
    def __init__(self, conn: aiosqlite.Connection):
        self.conn = conn

    async def create_conversation(
        self, title: str = "New Conversation", profile: str = "personal"
    ) -> Conversation:
        conv = Conversation(title=title, profile=profile)
        await self.conn.execute(
            "INSERT INTO conversations (id, title, profile, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (
                conv.id,
                conv.title,
                conv.profile,
                conv.created_at.isoformat(),
                conv.updated_at.isoformat(),
            ),
        )
        await self.conn.commit()
        return conv

    async def ensure_conversation(
        self,
        conversation_id: str,
        title: str = "New Conversation",
        profile: str = "personal",
    ) -> Conversation:
        existing = await self.get_conversation(conversation_id)
        if existing:
            return existing
        now = utc_now_iso()
        await self.conn.execute(
            "INSERT OR IGNORE INTO conversations (id, title, profile, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (conversation_id, title, profile, now, now),
        )
        await self.conn.commit()
        return Conversation(
            id=conversation_id,
            title=title,
            profile=profile,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
        )

    async def get_conversation(self, conversation_id: str) -> Conversation | None:
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

    async def list_conversations(self) -> list[Conversation]:
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
        cursor = await self.conn.execute(
            "DELETE FROM conversations WHERE id = ?", (conversation_id,)
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    async def update_conversation(
        self, conversation_id: str, title: str | None = None, profile: str | None = None
    ) -> Conversation | None:
        conv = await self.get_conversation(conversation_id)
        if not conv:
            return None
        new_title = title if title is not None else conv.title
        new_profile = profile if profile is not None else conv.profile
        now = utc_now_iso()
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

    async def export_conversation(self, conversation_id: str) -> dict | None:
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
        tool_calls: list | None = None,
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
            (
                msg.id,
                msg.conversation_id,
                msg.role.value,
                msg.content,
                tool_calls_json,
                msg.created_at.isoformat(),
            ),
        )
        # Update conversation updated_at
        await self.conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (utc_now_iso(), conversation_id),
        )
        await self.conn.commit()
        return msg

    async def get_messages(self, conversation_id: str) -> list[Message]:
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

    async def get_setting(self, key: str, default: str | None = None) -> str | None:
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

    # --- Task Persistence ---

    async def create_task(self, task: TaskState) -> TaskState:
        plan_json = json.dumps([step.model_dump(mode="json") for step in task.plan])
        artifacts_json = json.dumps(task.artifacts)
        await self.conn.execute(
            """
            INSERT INTO tasks (id, conversation_id, status, prompt, plan, current_step, artifacts, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.id,
                task.conversation_id,
                task.status.value,
                task.prompt,
                plan_json,
                task.current_step,
                artifacts_json,
                task.created_at.isoformat(),
                task.updated_at.isoformat(),
            ),
        )
        await self.conn.commit()
        return task

    async def get_task(self, task_id: str) -> TaskState | None:
        cursor = await self.conn.execute(
            """
            SELECT id, conversation_id, status, prompt, plan, current_step, artifacts, created_at, updated_at
            FROM tasks WHERE id = ?
            """,
            (task_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        raw_plan = json.loads(row["plan"]) if row["plan"] else []
        plan = [TaskPlanStep.model_validate(s) for s in raw_plan]
        artifacts = json.loads(row["artifacts"]) if row["artifacts"] else []
        return TaskState(
            id=row["id"],
            conversation_id=row["conversation_id"],
            status=TaskStatus(row["status"]),
            prompt=row["prompt"],
            plan=plan,
            current_step=row["current_step"],
            artifacts=artifacts,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    async def list_tasks(self, conversation_id: str | None = None) -> list[TaskState]:
        if conversation_id:
            cursor = await self.conn.execute(
                """
                SELECT id, conversation_id, status, prompt, plan, current_step, artifacts, created_at, updated_at
                FROM tasks WHERE conversation_id = ? ORDER BY created_at DESC
                """,
                (conversation_id,),
            )
        else:
            cursor = await self.conn.execute(
                """
                SELECT id, conversation_id, status, prompt, plan, current_step, artifacts, created_at, updated_at
                FROM tasks ORDER BY created_at DESC
                """
            )
        rows = await cursor.fetchall()
        tasks = []
        for r in rows:
            raw_plan = json.loads(r["plan"]) if r["plan"] else []
            plan = [TaskPlanStep.model_validate(s) for s in raw_plan]
            artifacts = json.loads(r["artifacts"]) if r["artifacts"] else []
            tasks.append(
                TaskState(
                    id=r["id"],
                    conversation_id=r["conversation_id"],
                    status=TaskStatus(r["status"]),
                    prompt=r["prompt"],
                    plan=plan,
                    current_step=r["current_step"],
                    artifacts=artifacts,
                    created_at=datetime.fromisoformat(r["created_at"]),
                    updated_at=datetime.fromisoformat(r["updated_at"]),
                )
            )
        return tasks

    async def update_task(self, task: TaskState) -> TaskState:
        now = utc_now_iso()
        task.updated_at = datetime.fromisoformat(now)
        plan_json = json.dumps([step.model_dump(mode="json") for step in task.plan])
        artifacts_json = json.dumps(task.artifacts)
        await self.conn.execute(
            """
            UPDATE tasks
            SET status = ?, plan = ?, current_step = ?, artifacts = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                task.status.value,
                plan_json,
                task.current_step,
                artifacts_json,
                now,
                task.id,
            ),
        )
        await self.conn.commit()
        return task

    async def delete_task(self, task_id: str) -> bool:
        cursor = await self.conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        await self.conn.commit()
        return cursor.rowcount > 0

    # --- Notes Persistence ---

    async def create_note(
        self, title: str, content: str, tags: list[str] | None = None
    ) -> dict[str, Any]:
        note_id = str(uuid.uuid4())
        tags_json = json.dumps(tags or [])
        now = utc_now_iso()
        await self.conn.execute(
            """
            INSERT INTO notes (id, title, content, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (note_id, title, content, tags_json, now, now),
        )
        await self.conn.commit()
        return {
            "id": note_id,
            "title": title,
            "content": content,
            "tags": tags or [],
            "created_at": now,
            "updated_at": now,
        }

    async def get_note(self, note_id: str) -> dict[str, Any] | None:
        cursor = await self.conn.execute(
            "SELECT id, title, content, tags, created_at, updated_at FROM notes WHERE id = ?",
            (note_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "title": row["title"],
            "content": row["content"],
            "tags": json.loads(row["tags"]) if row["tags"] else [],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    async def list_notes(self, query: str | None = None) -> list[dict[str, Any]]:
        if query:
            cursor = await self.conn.execute(
                """
                SELECT id, title, content, tags, created_at, updated_at
                FROM notes
                WHERE title LIKE ? OR content LIKE ?
                ORDER BY updated_at DESC
                """,
                (f"%{query}%", f"%{query}%"),
            )
        else:
            cursor = await self.conn.execute(
                "SELECT id, title, content, tags, created_at, updated_at FROM notes ORDER BY updated_at DESC"
            )
        rows = await cursor.fetchall()
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "content": r["content"],
                "tags": json.loads(r["tags"]) if r["tags"] else [],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]

    async def update_note(
        self,
        note_id: str,
        title: str | None = None,
        content: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any] | None:
        note = await self.get_note(note_id)
        if not note:
            return None
        new_title = title if title is not None else note["title"]
        new_content = content if content is not None else note["content"]
        new_tags = tags if tags is not None else note["tags"]
        now = utc_now_iso()
        await self.conn.execute(
            """
            UPDATE notes SET title = ?, content = ?, tags = ?, updated_at = ? WHERE id = ?
            """,
            (new_title, new_content, json.dumps(new_tags), now, note_id),
        )
        await self.conn.commit()
        return await self.get_note(note_id)

    async def delete_note(self, note_id: str) -> bool:
        cursor = await self.conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        await self.conn.commit()
        return cursor.rowcount > 0

    # --- MCP Server Persistence ---

    async def save_mcp_server(
        self,
        name: str,
        transport: str,
        command: str | None = None,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        url: str | None = None,
        server_id: str | None = None,
    ) -> dict[str, Any]:
        sid = server_id or str(uuid.uuid4())
        args_json = json.dumps(args or [])
        env_json = json.dumps(env or {})
        now = utc_now_iso()
        await self.conn.execute(
            """
            INSERT INTO mcp_servers (id, name, transport, command, args, env, url, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                transport = excluded.transport,
                command = excluded.command,
                args = excluded.args,
                env = excluded.env,
                url = excluded.url
            """,
            (sid, name, transport, command, args_json, env_json, url, now),
        )
        await self.conn.commit()
        return {
            "id": sid,
            "name": name,
            "transport": transport,
            "command": command,
            "args": args or [],
            "env": env or {},
            "url": url,
            "is_active": True,
            "created_at": now,
        }

    async def list_mcp_servers(self) -> list[dict[str, Any]]:
        cursor = await self.conn.execute(
            "SELECT id, name, transport, command, args, env, url, is_active, created_at FROM mcp_servers ORDER BY created_at ASC"
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "transport": r["transport"],
                "command": r["command"],
                "args": json.loads(r["args"]) if r["args"] else [],
                "env": json.loads(r["env"]) if r["env"] else {},
                "url": r["url"],
                "is_active": bool(r["is_active"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    async def delete_mcp_server(self, server_id: str) -> bool:
        cursor = await self.conn.execute(
            "DELETE FROM mcp_servers WHERE id = ?", (server_id,)
        )
        await self.conn.commit()
        return cursor.rowcount > 0
