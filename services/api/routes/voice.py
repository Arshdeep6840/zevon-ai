"""Voice endpoints for speech recognition, synthesis, wake-word, and state."""

from typing import Any

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from packages.shared_schemas.models import (
    SpeakRequest,
    TranscriptionResult,
    VoiceSettings,
    VoiceState,
    WakeCheckRequest,
)
from services.api.dependencies import get_repository
from services.memory.repository import MemoryRepository
from services.voice.manager import VoiceManager, get_voice_manager

router = APIRouter(prefix="/api/v1/voice", tags=["Voice"])


@router.get("/status")
async def get_voice_status(
    vm: VoiceManager = Depends(get_voice_manager),
):
    """Retrieve current voice state, wake-word configuration, and audio engine status."""
    return vm.get_status()


@router.get("/settings", response_model=VoiceSettings)
async def get_voice_settings(
    repo: MemoryRepository = Depends(get_repository),
    vm: VoiceManager = Depends(get_voice_manager),
):
    """Get persisted voice settings."""
    db_settings = await repo.get_all_settings()
    # Populate from DB or current manager defaults
    settings = VoiceSettings(
        wake_word_enabled=db_settings.get("voice_wake_word_enabled", "true").lower() == "true",
        wake_word_phrase=db_settings.get("voice_wake_word_phrase", "Hey Zevon"),
        wake_word_sensitivity=float(db_settings.get("voice_wake_word_sensitivity", 0.6)),
        tts_enabled=db_settings.get("voice_tts_enabled", "true").lower() == "true",
        tts_voice=db_settings.get("voice_tts_voice", "en_US-lessac-medium"),
        tts_speed=float(db_settings.get("voice_tts_speed", 1.0)),
        tts_volume=float(db_settings.get("voice_tts_volume", 1.0)),
        tts_muted=db_settings.get("voice_tts_muted", "false").lower() == "true",
        auto_barge_in=db_settings.get("voice_auto_barge_in", "true").lower() == "true",
        push_to_talk_key=db_settings.get("voice_push_to_talk_key", "Space"),
    )
    vm.update_settings(settings)
    return settings


@router.post("/settings", response_model=VoiceSettings)
async def update_voice_settings(
    payload: VoiceSettings,
    repo: MemoryRepository = Depends(get_repository),
    vm: VoiceManager = Depends(get_voice_manager),
):
    """Update and persist voice settings."""
    vm.update_settings(payload)
    # Persist to database
    await repo.set_setting("voice_wake_word_enabled", str(payload.wake_word_enabled).lower())
    await repo.set_setting("voice_wake_word_phrase", payload.wake_word_phrase)
    await repo.set_setting("voice_wake_word_sensitivity", str(payload.wake_word_sensitivity))
    await repo.set_setting("voice_tts_enabled", str(payload.tts_enabled).lower())
    await repo.set_setting("voice_tts_voice", payload.tts_voice)
    await repo.set_setting("voice_tts_speed", str(payload.tts_speed))
    await repo.set_setting("voice_tts_volume", str(payload.tts_volume))
    await repo.set_setting("voice_tts_muted", str(payload.tts_muted).lower())
    await repo.set_setting("voice_auto_barge_in", str(payload.auto_barge_in).lower())
    await repo.set_setting("voice_push_to_talk_key", payload.push_to_talk_key)
    return payload


@router.post("/transcribe", response_model=TranscriptionResult)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = "en",
    vm: VoiceManager = Depends(get_voice_manager),
):
    """Transcribe uploaded audio file using local ASR."""
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio payload")

    vm.state_machine.transition_to(VoiceState.TRANSCRIBING)
    result = await vm.asr.transcribe(audio_bytes, language=language)
    vm.state_machine.transition_to(VoiceState.IDLE)
    return result


@router.post("/speak")
async def text_to_speech(
    req: SpeakRequest,
    vm: VoiceManager = Depends(get_voice_manager),
):
    """Synthesize text into WAV audio using local TTS engine."""
    audio_wav = await vm.synthesize_speech(req)
    vm.finish_speaking()
    return Response(
        content=audio_wav,
        media_type="audio/wav",
        headers={
            "Content-Disposition": "inline; filename=speech.wav",
            "Cache-Control": "no-cache",
        },
    )


@router.post("/wake-check")
async def check_wake_word(
    req: WakeCheckRequest,
    vm: VoiceManager = Depends(get_voice_manager),
):
    """Test if a given text string or audio energy matches the wake phrase."""
    if req.text:
        detected, phrase, conf = vm.wake_detector.detect_in_text(req.text)
        if detected:
            vm.trigger_wake_detected(phrase)
        return {
            "detected": detected,
            "matched_phrase": phrase,
            "confidence": conf,
            "current_state": vm.current_state.value,
        }

    return {"detected": False, "confidence": 0.0, "current_state": vm.current_state.value}


@router.post("/state")
async def update_voice_state(
    state: VoiceState | None = Query(None),
    payload: Any = Body(None),
    vm: VoiceManager = Depends(get_voice_manager),
):
    """Directly request a voice state transition (e.g. push-to-talk start/end, barge-in)."""
    target_state = state
    if target_state is None and payload is not None:
        if isinstance(payload, dict):
            raw = payload.get("state")
        elif isinstance(payload, str):
            raw = payload
        else:
            raw = None
        if raw:
            try:
                target_state = VoiceState(raw.lower())
            except ValueError:
                pass

    if target_state is None:
        target_state = VoiceState.IDLE

    if target_state == VoiceState.INTERRUPTED:
        vm.trigger_barge_in()
    elif target_state == VoiceState.LISTENING:
        vm.trigger_push_to_talk_start()
    else:
        vm.state_machine.transition_to(target_state)
    return {"status": "success", "new_state": vm.current_state.value}
