"""Chat turn endpoint with streaming SSE and SQLite conversation persistence."""

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from packages.shared_schemas.models import ChatRequest, Message, Role
from packages.shared_schemas.profiles import get_profile
from services.api.config import settings
from services.api.dependencies import get_gateway, get_repository
from services.memory.repository import MemoryRepository
from services.model_gateway.registry import ModelRegistry

router = APIRouter(prefix="/api/v1", tags=["Chat"])


@router.post("/chat")
async def chat_turn(
    request: ChatRequest,
    repo: MemoryRepository = Depends(get_repository),
    gateway: ModelRegistry = Depends(get_gateway),
):
    """
    Submit a user message turn.
    Maintains short-term context, executes profile system prompt, persists messages,
    and streams tokens back via Server-Sent Events (SSE).
    """
    conversation_id = request.conversation_id
    conversation = None

    if conversation_id:
        conversation = await repo.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        # Create a new conversation automatically
        title_summary = request.message.strip().split("\n")[0][:45]
        active_profile_id = await repo.get_setting("active_profile", settings.default_profile)
        conversation = await repo.create_conversation(
            title=title_summary or "New Chat",
            profile=active_profile_id or "personal",
        )
        conversation_id = conversation.id

    # 1. Fetch history messages for short-term memory
    history = await repo.get_messages(conversation_id)

    # 2. Save user message to database
    await repo.add_message(
        conversation_id=conversation_id,
        role=Role.USER,
        content=request.message,
    )

    # 3. Assemble prompt context with Profile system prompt
    profile_def = get_profile(conversation.profile)
    effective_temp = (
        request.temperature if request.temperature != 0.7 else profile_def.default_temperature
    )

    context_messages: list[Message] = [
        Message(
            conversation_id=conversation_id,
            role=Role.SYSTEM,
            content=profile_def.system_prompt,
        )
    ]
    # Add prior history
    context_messages.extend(history)
    # Add current user turn
    context_messages.append(
        Message(
            conversation_id=conversation_id,
            role=Role.USER,
            content=request.message,
        )
    )

    # 4. Handle non-streaming mode
    if not request.stream:
        accumulated_text = []
        async for chunk in gateway.stream_chat(
            messages=context_messages,
            model_name=request.model_id,
            temperature=effective_temp,
        ):
            accumulated_text.append(chunk)

        full_response = "".join(accumulated_text)
        assistant_msg = await repo.add_message(
            conversation_id=conversation_id,
            role=Role.ASSISTANT,
            content=full_response,
        )
        return {
            "conversation_id": conversation_id,
            "message_id": assistant_msg.id,
            "role": "assistant",
            "content": full_response,
            "profile": conversation.profile,
        }

    # 5. Handle streaming mode via Server-Sent Events (SSE)
    async def sse_event_stream() -> AsyncIterator[str]:
        accumulated_chunks = []
        try:
            # First send meta event with conversation_id
            init_event = {
                "conversation_id": conversation_id,
                "profile": conversation.profile,
                "status": "started",
            }
            yield f"data: {json.dumps(init_event)}\n\n"

            async for delta in gateway.stream_chat(
                messages=context_messages,
                model_name=request.model_id,
                temperature=effective_temp,
            ):
                accumulated_chunks.append(delta)
                event_data = {
                    "conversation_id": conversation_id,
                    "delta": delta,
                }
                yield f"data: {json.dumps(event_data)}\n\n"

            # Stream finished - persist assistant message to DB
            full_content = "".join(accumulated_chunks)
            asst_msg = await repo.add_message(
                conversation_id=conversation_id,
                role=Role.ASSISTANT,
                content=full_content,
            )

            done_event = {
                "conversation_id": conversation_id,
                "message_id": asst_msg.id,
                "finish_reason": "stop",
                "delta": "",
            }
            yield f"data: {json.dumps(done_event)}\n\n"

        except Exception as e:
            err_event = {
                "conversation_id": conversation_id,
                "error": str(e),
                "finish_reason": "error",
            }
            yield f"data: {json.dumps(err_event)}\n\n"

    return StreamingResponse(
        sse_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
