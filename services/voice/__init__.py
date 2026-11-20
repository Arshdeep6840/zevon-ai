"""Voice subsystem for Zevon: wake-word, VAD, ASR, TTS, and state management."""

from .asr import BaseASRProvider, LocalWhisperASR
from .manager import VoiceManager, get_voice_manager
from .states import InvalidStateTransitionError, VoiceStateMachine
from .tts import BaseTTSProvider, LocalPiperTTS
from .vad import VoiceActivityDetector
from .wake_word import LocalWakeWordDetector

__all__ = [
    "BaseASRProvider",
    "BaseTTSProvider",
    "InvalidStateTransitionError",
    "LocalPiperTTS",
    "LocalWakeWordDetector",
    "LocalWhisperASR",
    "VoiceActivityDetector",
    "VoiceManager",
    "VoiceStateMachine",
    "get_voice_manager",
]
