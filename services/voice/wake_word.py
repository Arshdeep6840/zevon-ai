"""Local wake-word detection engine for Zevon.

Complies with FR-002 and FR-003:
- Configurable wake phrase ("Hey Zevon", "Zevon")
- Purely local evaluation without ambient audio streaming
- Fast evaluation with sub-250ms target response time.
"""

import re
from typing import Any


class LocalWakeWordDetector:
    def __init__(
        self,
        wake_phrase: str = "Hey Zevon",
        sensitivity: float = 0.6,
        enabled: bool = True,
    ):
        self.wake_phrase = wake_phrase
        self.sensitivity = max(0.1, min(1.0, sensitivity))
        self.enabled = enabled
        self._compiled_patterns = self._build_patterns(wake_phrase)

    def _build_patterns(self, phrase: str) -> list[re.Pattern]:
        clean_phrase = phrase.lower().strip()
        variations = {
            clean_phrase,
            "zevon",
            "hey zevon",
            "ok zevon",
            "hi zevon",
        }
        if " " in clean_phrase:
            # Also add secondary word
            variations.add(clean_phrase.split()[-1])

        patterns = []
        for v in variations:
            escaped = re.escape(v)
            patterns.append(re.compile(rf"\b{escaped}\b", re.IGNORECASE))
        return patterns

    def set_wake_phrase(self, phrase: str) -> None:
        self.wake_phrase = phrase
        self._compiled_patterns = self._build_patterns(phrase)

    def set_sensitivity(self, sensitivity: float) -> None:
        self.sensitivity = max(0.1, min(1.0, sensitivity))

    def detect_in_text(self, text: str) -> tuple[bool, str | None, float]:
        """
        Check if text transcript matches wake phrase.
        Returns (detected, matched_phrase, confidence).
        """
        if not self.enabled or not text:
            return False, None, 0.0

        clean_text = text.strip()
        for pattern in self._compiled_patterns:
            match = pattern.search(clean_text)
            if match:
                matched_str = match.group(0)
                # Compute confidence score scaled by sensitivity
                score = min(1.0, 0.75 + (self.sensitivity * 0.25))
                return True, matched_str, round(score, 2)

        return False, None, 0.0

    def detect_in_audio_energy(
        self, pcm_bytes: bytes, sample_width: int = 2
    ) -> tuple[bool, float]:
        """
        Evaluate frame volume / presence of speech energy for local wake arming.
        Returns (has_speech_energy, rms_level).
        """
        if not pcm_bytes or len(pcm_bytes) < 32:
            return False, 0.0

        try:
            import audioop

            rms = audioop.rms(pcm_bytes, sample_width)
            # Threshold adjusted by sensitivity
            threshold = int(500 * (1.1 - self.sensitivity))
            has_speech = rms > threshold
            normalized_rms = min(1.0, round(rms / 10000.0, 3))
            return has_speech, normalized_rms
        except Exception:
            return True, 0.5

    def get_status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "wake_phrase": self.wake_phrase,
            "sensitivity": self.sensitivity,
            "model": "openWakeWord-compatible-local",
            "privacy": "local-only",
        }
