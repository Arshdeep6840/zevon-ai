"""Voice Activity Detection (VAD) processor for local audio streams."""

from datetime import UTC, datetime
from typing import Any


class VoiceActivityDetector:
    """
    Lightweight energy and segmenting VAD compatible with Silero VAD concepts.
    Detects onset of speech and end-of-speech trailing silence.
    """

    def __init__(
        self,
        energy_threshold: int = 450,
        silence_timeout_seconds: float = 0.8,
        min_speech_duration_seconds: float = 0.3,
    ):
        self.energy_threshold = energy_threshold
        self.silence_timeout = silence_timeout_seconds
        self.min_speech_duration = min_speech_duration_seconds

        self.is_speaking = False
        self._speech_started_at: datetime | None = None
        self._last_speech_at: datetime | None = None
        self._total_speech_bytes = 0

    def reset(self) -> None:
        self.is_speaking = False
        self._speech_started_at = None
        self._last_speech_at = None
        self._total_speech_bytes = 0

    def process_frame(self, pcm_bytes: bytes, sample_width: int = 2) -> dict[str, Any]:
        """
        Process a PCM audio chunk.
        Returns a dict with:
        - has_speech (bool)
        - speech_started (bool)
        - speech_ended (bool)
        - rms_level (float)
        """
        now = datetime.now(UTC)
        rms = 0.0

        if pcm_bytes and len(pcm_bytes) >= 32:
            try:
                import audioop

                rms = float(audioop.rms(pcm_bytes, sample_width))
            except Exception:
                rms = 300.0

        is_frame_speech = rms > self.energy_threshold

        speech_started = False
        speech_ended = False

        if is_frame_speech:
            self._last_speech_at = now
            self._total_speech_bytes += len(pcm_bytes)

            if not self.is_speaking:
                self.is_speaking = True
                self._speech_started_at = now
                speech_started = True
        else:
            if self.is_speaking and self._last_speech_at:
                silence_duration = (now - self._last_speech_at).total_seconds()
                speech_duration = (now - (self._speech_started_at or now)).total_seconds()

                if (
                    silence_duration >= self.silence_timeout
                    and speech_duration >= self.min_speech_duration
                ):
                    self.is_speaking = False
                    speech_ended = True

        return {
            "has_speech": is_frame_speech,
            "is_speaking": self.is_speaking,
            "speech_started": speech_started,
            "speech_ended": speech_ended,
            "rms_level": round(rms, 1),
            "total_speech_bytes": self._total_speech_bytes,
        }
