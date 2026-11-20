"""Voice Manager coordinating wake-word, VAD, ASR, TTS, and state transitions."""

from typing import Any

from packages.shared_schemas.models import (
    SpeakRequest,
    TranscriptionResult,
    VoiceSettings,
    VoiceState,
)

from .asr import LocalWhisperASR
from .states import VoiceStateMachine
from .tts import LocalPiperTTS
from .vad import VoiceActivityDetector
from .wake_word import LocalWakeWordDetector


class VoiceManager:
    """
    Central coordinator for Zevon's Phase 2 voice assistant loop.
    Enforces local-first execution, barge-in interruption, and state synchronization.
    """

    def __init__(self, settings: VoiceSettings | None = None):
        self.settings = settings or VoiceSettings()
        self.state_machine = VoiceStateMachine(VoiceState.IDLE)
        self.wake_detector = LocalWakeWordDetector(
            wake_phrase=self.settings.wake_word_phrase,
            sensitivity=self.settings.wake_word_sensitivity,
            enabled=self.settings.wake_word_enabled,
        )
        self.vad = VoiceActivityDetector()
        self.asr = LocalWhisperASR()
        self.tts = LocalPiperTTS(default_voice=self.settings.tts_voice)
        self.tts.set_muted(self.settings.tts_muted)

        self._active_audio_buffer = bytearray()
        self._interrupted = False

    @property
    def current_state(self) -> VoiceState:
        return self.state_machine.current_state

    def update_settings(self, new_settings: VoiceSettings) -> None:
        self.settings = new_settings
        self.wake_detector.enabled = new_settings.wake_word_enabled
        self.wake_detector.set_wake_phrase(new_settings.wake_word_phrase)
        self.wake_detector.set_sensitivity(new_settings.wake_word_sensitivity)
        self.tts.default_voice = new_settings.tts_voice
        self.tts.set_muted(new_settings.tts_muted)

    def trigger_wake_detected(self, phrase: str | None = None) -> None:
        self.state_machine.transition_to(
            VoiceState.WAKE_DETECTED, {"phrase": phrase or self.settings.wake_word_phrase}
        )
        # Immediately move to listening
        self.state_machine.transition_to(VoiceState.LISTENING)
        self.vad.reset()
        self._active_audio_buffer.clear()
        self._interrupted = False

    def trigger_push_to_talk_start(self) -> None:
        if self.current_state == VoiceState.SPEAKING:
            self.trigger_barge_in()
        self.state_machine.transition_to(VoiceState.LISTENING)
        self.vad.reset()
        self._active_audio_buffer.clear()
        self._interrupted = False

    def trigger_push_to_talk_end(self) -> None:
        if self.current_state == VoiceState.LISTENING:
            self.state_machine.transition_to(VoiceState.TRANSCRIBING)

    def trigger_barge_in(self) -> None:
        """Interrupt active speech output and return to listening or idle."""
        self._interrupted = True
        if self.current_state in {VoiceState.SPEAKING, VoiceState.THINKING}:
            self.state_machine.transition_to(VoiceState.INTERRUPTED)
            self.state_machine.transition_to(VoiceState.LISTENING)

    def process_incoming_audio_chunk(self, chunk: bytes, sample_width: int = 2) -> dict[str, Any]:
        """
        Process an incoming audio frame from WebSocket or audio stream.
        Applies local VAD and wake-word checks without streaming audio to external servers.
        """
        vad_res = self.vad.process_frame(chunk, sample_width)
        event_info = {
            "state": self.current_state.value,
            "vad": vad_res,
            "wake_word": None,
        }

        # If IDLE and wake word enabled, check audio energy
        if self.current_state == VoiceState.IDLE and self.settings.wake_word_enabled:
            has_energy, level = self.wake_detector.detect_in_audio_energy(chunk, sample_width)
            if has_energy and level > (1.1 - self.settings.wake_word_sensitivity):
                event_info["wake_word"] = {"candidate": True, "level": level}

        # If LISTENING, buffer audio for ASR
        if self.current_state == VoiceState.LISTENING:
            self._active_audio_buffer.extend(chunk)

            # Check if user spoke and then stopped (trailing silence)
            if vad_res["speech_ended"]:
                self.state_machine.transition_to(VoiceState.TRANSCRIBING)
                event_info["speech_ended"] = True

        return event_info

    async def transcribe_current_buffer(self, language: str = "en") -> TranscriptionResult:
        """Transcribe the captured audio buffer."""
        self.state_machine.transition_to(VoiceState.TRANSCRIBING)
        audio_data = bytes(self._active_audio_buffer)
        result = await self.asr.transcribe(audio_data, language=language)
        self._active_audio_buffer.clear()
        return result

    async def synthesize_speech(self, req: SpeakRequest) -> bytes:
        """Synthesize assistant response text to speech audio."""
        self.state_machine.transition_to(VoiceState.SPEAKING)
        audio = await self.tts.synthesize(
            text=req.text,
            voice=req.voice or self.settings.tts_voice,
            speed=req.speed * self.settings.tts_speed,
            volume=req.volume * self.settings.tts_volume,
        )
        return audio

    def finish_speaking(self) -> None:
        if self.current_state == VoiceState.SPEAKING:
            self.state_machine.transition_to(VoiceState.IDLE)

    def get_status(self) -> dict[str, Any]:
        return {
            "current_state": self.current_state.value,
            "wake_word": self.wake_detector.get_status(),
            "vad_speaking": self.vad.is_speaking,
            "tts_muted": self.tts.is_muted,
            "settings": self.settings.model_dump(),
        }


_global_voice_manager: VoiceManager | None = None


def get_voice_manager() -> VoiceManager:
    global _global_voice_manager
    if _global_voice_manager is None:
        _global_voice_manager = VoiceManager()
    return _global_voice_manager
