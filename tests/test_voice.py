"""Unit and integration tests for Phase 2 Voice Assistant subsystem."""

import io
import wave
import pytest
from fastapi.testclient import TestClient

from packages.shared_schemas.models import SpeakRequest, VoiceSettings, VoiceState
from services.api.config import settings
from services.api.main import app
from services.model_gateway.registry import get_model_registry
from services.voice.asr import LocalWhisperASR
from services.voice.manager import VoiceManager
from services.voice.states import InvalidStateTransitionError, VoiceStateMachine
from services.voice.tts import LocalPiperTTS
from services.voice.vad import VoiceActivityDetector
from services.voice.wake_word import LocalWakeWordDetector


@pytest.fixture(autouse=True)
def setup_voice_test_env(tmp_path):
    test_db = str(tmp_path / "voice_test.db")
    settings.db_path = test_db
    get_model_registry().set_force_offline(True)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_voice_state_machine_lifecycle():
    sm = VoiceStateMachine(VoiceState.IDLE)
    assert sm.current_state == VoiceState.IDLE

    # Valid path: IDLE -> WAKE_DETECTED -> LISTENING -> TRANSCRIBING -> THINKING -> SPEAKING -> IDLE
    assert sm.transition_to(VoiceState.WAKE_DETECTED) == VoiceState.WAKE_DETECTED
    assert sm.transition_to(VoiceState.LISTENING) == VoiceState.LISTENING
    assert sm.transition_to(VoiceState.TRANSCRIBING) == VoiceState.TRANSCRIBING
    assert sm.transition_to(VoiceState.THINKING) == VoiceState.THINKING
    assert sm.transition_to(VoiceState.SPEAKING) == VoiceState.SPEAKING
    assert sm.transition_to(VoiceState.IDLE) == VoiceState.IDLE

    # Barge-in transition: SPEAKING -> INTERRUPTED -> LISTENING
    sm.transition_to(VoiceState.LISTENING)
    sm.transition_to(VoiceState.TRANSCRIBING)
    sm.transition_to(VoiceState.THINKING)
    sm.transition_to(VoiceState.SPEAKING)
    assert sm.transition_to(VoiceState.INTERRUPTED) == VoiceState.INTERRUPTED
    assert sm.transition_to(VoiceState.LISTENING) == VoiceState.LISTENING

    # Invalid transition should raise
    with pytest.raises(InvalidStateTransitionError):
        sm.transition_to(VoiceState.SPEAKING)


def test_wake_word_detector():
    detector = LocalWakeWordDetector(wake_phrase="Hey Zevon", sensitivity=0.6)

    # Positive matches
    detected, phrase, conf = detector.detect_in_text("Hey Zevon, what is the weather?")
    assert detected is True
    assert "zevon" in phrase.lower()
    assert conf >= 0.7

    detected_short, _, _ = detector.detect_in_text("Zevon, open my notes")
    assert detected_short is True

    # Negative match
    neg_detected, _, _ = detector.detect_in_text("Hello Siri, play music")
    assert neg_detected is False

    # Audio energy check
    # Generate 16-bit PCM silent buffer
    silent_pcm = b"\x00\x00" * 100
    has_energy, level = detector.detect_in_audio_energy(silent_pcm)
    assert has_energy is False
    assert level == 0.0


def test_vad_speech_segmentation():
    vad = VoiceActivityDetector(energy_threshold=200, silence_timeout_seconds=0.1)

    # 1. Silent frame
    res_silence = vad.process_frame(b"\x00\x00" * 50)
    assert res_silence["has_speech"] is False
    assert res_silence["is_speaking"] is False

    # 2. Loud frame (simulated speech)
    loud_frame = b"\x50\x20" * 50
    res_loud = vad.process_frame(loud_frame)
    assert res_loud["is_speaking"] is True
    assert res_loud["speech_started"] is True


@pytest.mark.asyncio
async def test_whisper_asr():
    asr = LocalWhisperASR()
    # Empty audio
    res_empty = await asr.transcribe(b"")
    assert res_empty.text == ""

    # Simulated audio buffer
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x20\x10" * 1600)  # 0.1s
    res = await asr.transcribe(buf.getvalue(), language="en")
    assert res.language == "en"
    assert len(res.text) > 0


@pytest.mark.asyncio
async def test_piper_tts():
    tts = LocalPiperTTS()
    # Synthesize audio
    wav_bytes = await tts.synthesize("Hello from Zevon assistant.", speed=1.2, volume=0.8)
    assert len(wav_bytes) > 44  # Valid WAV header + frames
    assert wav_bytes.startswith(b"RIFF")

    # Muted synthesis
    tts.set_muted(True)
    muted_wav = await tts.synthesize("Muted speech")
    assert len(muted_wav) > 0
    assert muted_wav.startswith(b"RIFF")


@pytest.mark.asyncio
async def test_voice_manager_barge_in():
    vm = VoiceManager()
    assert vm.current_state == VoiceState.IDLE

    # Simulate speaking
    await vm.synthesize_speech(SpeakRequest(text="Speaking some long text"))
    assert vm.current_state == VoiceState.SPEAKING

    # Trigger barge in
    vm.trigger_barge_in()
    assert vm.current_state == VoiceState.LISTENING


def test_voice_api_endpoints(client):
    # 1. Status
    res_status = client.get("/api/v1/voice/status")
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert "current_state" in status_data
    assert "wake_word" in status_data

    # 2. Settings
    res_settings = client.get("/api/v1/voice/settings")
    assert res_settings.status_code == 200
    voice_cfg = res_settings.json()
    assert voice_cfg["wake_word_phrase"] == "Hey Zevon"

    # Update settings
    updated_payload = voice_cfg.copy()
    updated_payload["wake_word_phrase"] = "Zevon"
    updated_payload["tts_speed"] = 1.1
    res_post_settings = client.post("/api/v1/voice/settings", json=updated_payload)
    assert res_post_settings.status_code == 200
    assert res_post_settings.json()["wake_word_phrase"] == "Zevon"

    # 3. Wake Check
    res_wake = client.post("/api/v1/voice/wake-check", json={"text": "Zevon, what time is it?"})
    assert res_wake.status_code == 200
    assert res_wake.json()["detected"] is True

    # 4. Speak
    res_speak = client.post("/api/v1/voice/speak", json={"text": "Voice test playback", "speed": 1.0})
    assert res_speak.status_code == 200
    assert res_speak.headers["content-type"] == "audio/wav"
    assert len(res_speak.content) > 44

    # 5. State transition
    res_state = client.post("/api/v1/voice/state?state=listening")
    assert res_state.status_code == 200
    assert res_state.json()["new_state"] == "listening"
