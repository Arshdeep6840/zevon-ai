"""Voice state machine managing transitions across voice interaction lifecycle."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from packages.shared_schemas.models import VoiceState


class InvalidStateTransitionError(Exception):
    """Raised when an illegal voice state transition is attempted."""


class VoiceStateMachine:
    """
    Coordinates voice states according to SRS Section 10.1:
    IDLE/ARMED -> WAKE_DETECTED -> LISTENING -> TRANSCRIBING -> THINKING ->
    SPEAKING -> INTERRUPTED / IDLE.
    """

    ALLOWED_TRANSITIONS: dict[VoiceState, set[VoiceState]] = {
        VoiceState.IDLE: {
            VoiceState.WAKE_DETECTED,
            VoiceState.LISTENING,
            VoiceState.TRANSCRIBING,
            VoiceState.THINKING,
            VoiceState.SPEAKING,
            VoiceState.MIC_UNAVAILABLE,
            VoiceState.ERROR,
        },
        VoiceState.WAKE_DETECTED: {
            VoiceState.LISTENING,
            VoiceState.IDLE,
            VoiceState.ERROR,
        },
        VoiceState.LISTENING: {
            VoiceState.TRANSCRIBING,
            VoiceState.SPEAKING,
            VoiceState.IDLE,
            VoiceState.ERROR,
            VoiceState.INTERRUPTED,
        },
        VoiceState.TRANSCRIBING: {
            VoiceState.THINKING,
            VoiceState.LISTENING,
            VoiceState.IDLE,
            VoiceState.ERROR,
        },
        VoiceState.THINKING: {
            VoiceState.SPEAKING,
            VoiceState.WAITING_APPROVAL,
            VoiceState.INTERRUPTED,
            VoiceState.IDLE,
            VoiceState.ERROR,
        },
        VoiceState.WAITING_APPROVAL: {
            VoiceState.THINKING,
            VoiceState.SPEAKING,
            VoiceState.IDLE,
            VoiceState.ERROR,
        },
        VoiceState.SPEAKING: {
            VoiceState.INTERRUPTED,
            VoiceState.IDLE,
            VoiceState.LISTENING,
            VoiceState.ERROR,
        },
        VoiceState.INTERRUPTED: {
            VoiceState.LISTENING,
            VoiceState.IDLE,
            VoiceState.ERROR,
        },
        VoiceState.MIC_UNAVAILABLE: {
            VoiceState.IDLE,
            VoiceState.ERROR,
        },
        VoiceState.ERROR: {
            VoiceState.IDLE,
            VoiceState.LISTENING,
        },
    }

    def __init__(self, initial_state: VoiceState = VoiceState.IDLE):
        self._state = initial_state
        self._last_transition = datetime.now(UTC)
        self._listeners: list[Callable[[VoiceState, VoiceState, dict[str, Any]], None]] = []

    @property
    def current_state(self) -> VoiceState:
        return self._state

    @property
    def time_in_current_state(self) -> float:
        return (datetime.now(UTC) - self._last_transition).total_seconds()

    def add_listener(
        self, callback: Callable[[VoiceState, VoiceState, dict[str, Any]], None]
    ) -> None:
        self._listeners.append(callback)

    def remove_listener(
        self, callback: Callable[[VoiceState, VoiceState, dict[str, Any]], None]
    ) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    def transition_to(
        self, new_state: VoiceState, metadata: dict[str, Any] | None = None
    ) -> VoiceState:
        """Attempt to transition to a new voice state."""
        if new_state == self._state:
            return self._state

        allowed = self.ALLOWED_TRANSITIONS.get(self._state, set())
        # Error and Idle states can be forced if needed
        if new_state not in allowed and new_state not in {VoiceState.IDLE, VoiceState.ERROR}:
            raise InvalidStateTransitionError(
                f"Cannot transition voice state from {self._state.value} to {new_state.value}"
            )

        old_state = self._state
        self._state = new_state
        self._last_transition = datetime.now(UTC)

        meta = metadata or {}
        for listener in self._listeners:
            try:
                listener(old_state, new_state, meta)
            except Exception:
                pass

        return self._state

    def reset(self) -> None:
        self.transition_to(VoiceState.IDLE)
