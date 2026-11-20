"""Conversation and message history management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from packages.shared_schemas.models import Conversation
from services.api.dependencies import get_repository
from services.memory.repository import MemoryRepository

router = APIRouter(prefix="/api/v1/conversations", tags=["Conversations"])


class CreateConversationRequest(BaseModel):
    title: str = "New Conversation"
    profile: str = "personal"


class UpdateConversationRequest(BaseModel):
    title: str | None = None
    profile: str | None = None


@router.get("", response_model=list[Conversation])
async def list_conversations(repo: MemoryRepository = Depends(get_repository)):
    """List all saved conversations ordered by recency."""
    return await repo.list_conversations()


@router.post("", response_model=Conversation)
async def create_conversation(
    payload: CreateConversationRequest,
    repo: MemoryRepository = Depends(get_repository),
):
    """Create a new conversation session."""
    return await repo.create_conversation(title=payload.title, profile=payload.profile)


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    repo: MemoryRepository = Depends(get_repository),
):
    """Retrieve conversation details and chronological message history."""
    conv = await repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await repo.get_messages(conversation_id)
    return {
        "conversation": conv,
        "messages": messages,
    }


@router.patch("/{conversation_id}", response_model=Conversation)
async def update_conversation(
    conversation_id: str,
    payload: UpdateConversationRequest,
    repo: MemoryRepository = Depends(get_repository),
):
    """Update title or active profile of a conversation."""
    updated = await repo.update_conversation(
        conversation_id=conversation_id,
        title=payload.title,
        profile=payload.profile,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return updated


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    repo: MemoryRepository = Depends(get_repository),
):
    """Permanently delete a conversation and its messages."""
    success = await repo.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "deleted_id": conversation_id}


@router.delete("")
async def clear_all_conversations(repo: MemoryRepository = Depends(get_repository)):
    """Clear all conversations and message history (user privacy reset)."""
    count = await repo.clear_all_conversations()
    return {"status": "success", "cleared_conversations": count}


@router.get("/{conversation_id}/export")
async def export_conversation(
    conversation_id: str,
    format: str = Query("json", pattern="^(json|markdown)$"),
    repo: MemoryRepository = Depends(get_repository),
):
    """Export conversation data in portable JSON or Markdown format."""
    conv = await repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await repo.get_messages(conversation_id)

    if format == "json":
        return {
            "conversation": conv.model_dump(mode="json"),
            "messages": [m.model_dump(mode="json") for m in messages],
        }

    # Markdown format
    lines = [
        f"# {conv.title}",
        f"**Profile:** {conv.profile}  ",
        f"**Date:** {conv.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
        "",
        "---",
        "",
    ]
    for msg in messages:
        sender = msg.role.value.capitalize()
        lines.append(f"### {sender}")
        lines.append(msg.content)
        lines.append("")

    return {"markdown": "\n".join(lines)}
