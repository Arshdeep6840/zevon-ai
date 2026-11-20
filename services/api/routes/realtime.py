"""Realtime WebSocket endpoint for low-latency streaming and interruption."""

import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from packages.shared_schemas.models import Message, Role
from packages.shared_schemas.profiles import get_profile
from services.memory.database import get_db
from services.memory.repository import MemoryRepository
from services.model_gateway.registry import get_model_registry
from services.api.config import settings

router = APIRouter(prefix="/api/v1", tags=["Realtime"])


@router.websocket("/realtime")
async def realtime_chat_socket(websocket: WebSocket):
    """
    Bidirectional streaming WebSocket.
    Supports streaming response tokens, interrupt cancellation (barge-in), and ping/pong.
    """
    await websocket.accept()
    gateway = get_model_registry(ollama_url=settings.ollama_url)
    active_stream_task: asyncio.Task | None = None
    interrupted = False

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON format"})
                continue

            msg_type = data.get("type", "chat")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type == "interrupt":
                interrupted = True
                if active_stream_task and not active_stream_task.done():
                    active_stream_task.cancel()
                await websocket.send_json({"type": "interrupted"})
                continue

            if msg_type == "chat":
                # Cancel previous generation if still running
                if active_stream_task and not active_stream_task.done():
                    active_stream_task.cancel()

                user_text = data.get("message", "").strip()
                if not user_text:
                    continue

                conversation_id = data.get("conversation_id")
                model_id = data.get("model_id")
                temperature = float(data.get("temperature", 0.7))

                interrupted = False

                async def process_chat(conv_id: str | None, text: str):
                    active_cid = conv_id
                    async for conn in get_db():
                        repo = MemoryRepository(conn)
                        if not active_cid:
                            title = text[:40] or "New Chat"
                            active_prof = await repo.get_setting("active_profile", settings.default_profile)
                            c = await repo.create_conversation(title=title, profile=active_prof or "personal")
                            active_cid = c.id
                        else:
                            c = await repo.get_conversation(active_cid)
                            if not c:
                                c = await repo.create_conversation(title=text[:40], profile=settings.default_profile)
                                active_cid = c.id

                        # Save user message
                        await repo.add_message(active_cid, Role.USER, text)
                        history = await repo.get_messages(active_cid)

                        profile_def = get_profile(c.profile)
                        context: list[Message] = [
                            Message(conversation_id=active_cid, role=Role.SYSTEM, content=profile_def.system_prompt)
                        ]
                        context.extend(history)

                        await websocket.send_json({
                            "type": "start",
                            "conversation_id": active_cid,
                            "profile": c.profile
                        })

                        accumulated = []
                        try:
                            async for delta in gateway.stream_chat(
                                messages=context,
                                model_name=model_id,
                                temperature=temperature,
                            ):
                                if interrupted:
                                    break
                                accumulated.append(delta)
                                await websocket.send_json({
                                    "type": "delta",
                                    "delta": delta,
                                    "conversation_id": active_cid
                                })

                            full_content = "".join(accumulated)
                            asst_msg = await repo.add_message(active_cid, Role.ASSISTANT, full_content)

                            await websocket.send_json({
                                "type": "done",
                                "conversation_id": active_cid,
                                "message_id": asst_msg.id,
                                "interrupted": interrupted,
                            })
                        except asyncio.CancelledError:
                            if accumulated:
                                await repo.add_message(active_cid, Role.ASSISTANT, "".join(accumulated))
                            await websocket.send_json({"type": "cancelled", "conversation_id": active_cid})
                        except Exception as ex:
                            await websocket.send_json({"type": "error", "error": str(ex)})

                active_stream_task = asyncio.create_task(process_chat(conversation_id, user_text))

    except WebSocketDisconnect:
        if active_stream_task and not active_stream_task.done(