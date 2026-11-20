"""Realtime WebSocket endpoint for low-latency streaming, voice interaction, and barge-in."""

import asyncio
import base64
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from packages.shared_schemas.models import Message, Role, SpeakRequest, VoiceState
from packages.shared_schemas.profiles import get_profile
from services.api.config import settings
from services.memory.database import get_db
from services.memory.repository import MemoryRepository
from services.model_gateway.registry import get_model_registry
from services.voice.manager import get_voice_manager

router = APIRouter(prefix="/api/v1", tags=["Realtime"])


@router.websocket("/realtime")
async def realtime_chat_socket(websocket: WebSocket):
    """
    Bidirectional streaming WebSocket.
    Supports streaming response tokens, interrupt cancellation (barge-in),
    wake-word detection, voice state synchronization, and TTS audio playback.
    """
    await websocket.accept()
    gateway = get_model_registry(ollama_url=settings.ollama_url)
    vm = get_voice_manager()
    active_stream_task: asyncio.Task | None = None
    interrupt_event = asyncio.Event()

    # Forward voice state machine changes to client over WebSocket
    def on_voice_state_changed(old_state: VoiceState, new_state: VoiceState, meta: dict):
        try:
            asyncio.create_task(
                websocket.send_json(
                    {
                        "type": "voice_state_changed",
                        "old_state": old_state.value,
                        "new_state": new_state.value,
                        "meta": meta,
                    }
                )
            )
        except Exception:
            pass

    vm.state_machine.add_listener(on_voice_state_changed)

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
                interrupt_event.set()
                vm.trigger_barge_in()
                if active_stream_task and not active_stream_task.done():
                    active_stream_task.cancel()
                await websocket.send_json(
                    {"type": "interrupted", "voice_state": vm.current_state.value}
                )
                continue

            if msg_type == "voice_state":
                req_state = data.get("state")
                try:
                    if req_state:
                        target = VoiceState(req_state)
                        if target == VoiceState.INTERRUPTED:
                            vm.trigger_barge_in()
                        elif target == VoiceState.LISTENING:
                            vm.trigger_push_to_talk_start()
                        else:
                            vm.state_machine.transition_to(target)
                        await websocket.send_json(
                            {
                                "type": "voice_state_ack",
                                "current_state": vm.current_state.value,
                            }
                        )
                except Exception as ex:
                    await websocket.send_json({"type": "error", "error": str(ex)})
                continue

            if msg_type == "wake_check":
                text = data.get("text", "")
                detected, phrase, conf = vm.wake_detector.detect_in_text(text)
                if detected:
                    vm.trigger_wake_detected(phrase)
                    await websocket.send_json(
                        {
                            "type": "wake_word_detected",
                            "phrase": phrase,
                            "confidence": conf,
                            "voice_state": vm.current_state.value,
                        }
                    )
                else:
                    await websocket.send_json({"type": "wake_word_not_detected"})
                continue

            if msg_type == "tts_speak":
                text_to_speak = data.get("text", "")
                if text_to_speak:
                    audio_wav = await vm.synthesize_speech(
                        SpeakRequest(
                            text=text_to_speak,
                            voice=data.get("voice"),
                            speed=float(data.get("speed", 1.0)),
                            volume=float(data.get("volume", 1.0)),
                        )
                    )
                    vm.finish_speaking()
                    await websocket.send_json(
                        {
                            "type": "tts_audio",
                            "audio_base64": base64.b64encode(audio_wav).decode("ascii"),
                            "format": "wav",
                            "voice_state": vm.current_state.value,
                        }
                    )
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
                enable_voice_reply = bool(data.get("voice_reply", False))

                interrupt_event = asyncio.Event()

                async def process_chat(
                    conv_id: str | None,
                    text: str,
                    model_name: str | None,
                    temp: float,
                    voice_reply: bool,
                    stop_evt: asyncio.Event,
                ):
                    vm.state_machine.transition_to(VoiceState.THINKING)
                    active_cid = conv_id
                    async for conn in get_db(settings.db_path):
                        repo = MemoryRepository(conn)
                        if not active_cid:
                            title = text[:40] or "New Chat"
                            active_prof = await repo.get_setting(
                                "active_profile", settings.default_profile
                            )
                            c = await repo.create_conversation(
                                title=title, profile=active_prof or "personal"
                            )
                            active_cid = c.id
                        else:
                            c = await repo.get_conversation(active_cid)
                            if not c:
                                c = await repo.create_conversation(
                                    title=text[:40], profile=settings.default_profile
                                )
                                active_cid = c.id

                        # Save user message
                        await repo.add_message(active_cid, Role.USER, text)
                        history = await repo.get_messages(active_cid)

                        profile_def = get_profile(c.profile)
                        context: list[Message] = [
                            Message(
                                conversation_id=active_cid,
                                role=Role.SYSTEM,
                                content=profile_def.system_prompt,
                            )
                        ]
                        context.extend(history)

                        await websocket.send_json(
                            {"type": "start", "conversation_id": active_cid, "profile": c.profile}
                        )

                        accumulated = []
                        try:
                            async for delta in gateway.stream_chat(
                                messages=context,
                                model_name=model_name,
                                temperature=temp,
                            ):
                                if stop_evt.is_set():
                                    break
                                accumulated.append(delta)
                                await websocket.send_json(
                                    {"type": "delta", "delta": delta, "conversation_id": active_cid}
                                )

                            full_content = "".join(accumulated)
                            asst_msg = await repo.add_message(
                                active_cid, Role.ASSISTANT, full_content
                            )

                            await websocket.send_json(
                                {
                                    "type": "done",
                                    "conversation_id": active_cid,
                                    "message_id": asst_msg.id,
                                    "interrupted": stop_evt.is_set(),
                                }
                            )

                            # If voice reply was enabled and not interrupted, synthesize audio
                            if voice_reply and not stop_evt.is_set() and full_content:
                                vm.state_machine.transition_to(VoiceState.SPEAKING)
                                audio_wav = await vm.synthesize_speech(
                                    SpeakRequest(text=full_content[:300])
                                )
                                vm.finish_speaking()
                                await websocket.send_json(
                                    {
                                        "type": "tts_audio",
                                        "audio_base64": base64.b64encode(audio_wav).decode(
                                            "ascii"
                                        ),
                                        "format": "wav",
                                    }
                                )
                            else:
                                vm.state_machine.transition_to(VoiceState.IDLE)

                        except asyncio.CancelledError:
                            if accumulated:
                                await repo.add_message(
                                    active_cid, Role.ASSISTANT, "".join(accumulated)
                                )
                            vm.state_machine.transition_to(VoiceState.IDLE)
                            await websocket.send_json(
                                {"type": "cancelled", "conversation_id": active_cid}
                            )
                        except Exception as ex:
                            vm.state_machine.transition_to(VoiceState.ERROR)
                            await websocket.send_json({"type": "error", "error": str(ex)})

                active_stream_task = asyncio.create_task(
                    process_chat(
                        conversation_id,
                        user_text,
                        model_id,
                        temperature,
                        enable_voice_reply,
                        interrupt_event,
                    )
                )

    except WebSocketDisconnect:
        vm.state_machine.remove_listener(on_voice_state_changed)
        if active_stream_task and not active_stream_task.done():
            active_stream_task.cancel()
