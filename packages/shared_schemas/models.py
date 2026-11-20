"""Data contracts and schemas for Zevon."""

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class RiskLevel(str, Enum):
    R0 = "R0"  # Read-only
    R1 = "R1"  # Reversible local change
    R2 = "R2"  # External or destructive
    R3 = "R3"  # High impact / critical


class VoiceState(str, Enum):
    IDLE = "idle"
    WAKE_DETECTED = "wake_detected"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    THINKING = "thinking"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    WAITING_APPROVAL = "waiting_approval"
    ERROR = "error"
    MIC_UNAVAILABLE = "mic_unavailable"


class VoiceSettings(BaseModel):
    wake_word_enabled: bool = True
    wake_word_phrase: str = "Hey Zevon"
    wake_word_sensitivity: float = 0.6
    tts_enabled: bool = True
    tts_voice: str = "en_US-lessac-medium"
    tts_speed: float = 1.0
    tts_volume: float = 1.0
    tts_muted: bool = False
    auto_barge_in: bool = True
    push_to_talk_key: str = "Space"


class TranscriptionResult(BaseModel):
    text: str
    language: str = "en"
    duration_seconds: float = 0.0
    confidence: float = 1.0


class SpeakRequest(BaseModel):
    text: str
    voice: str | None = None
    speed: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0


class WakeCheckRequest(BaseModel):
    text: str | None = None
    audio_base64: str | None = None
    sensitivity: float = 0.6


class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    role: Role
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    created_at: datetime = Field(default_factory=utc_now)


class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "New Conversation"
    profile: str = "personal"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ModelCard(BaseModel):
    id: str
    name: str
    provider: str
    parameter_size: str = "compact"
    quantization: str | None = None
    context_length: int = 4096
    is_active: bool = False
    is_installed: bool = True
    description: str | None = None


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str
    model_id: str | None = None
    stream: bool = True
    temperature: float = 0.7


class ChatChunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    delta: str
    finish_reason: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class TaskStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPlanStep(BaseModel):
    step_id: int
    title: str
    tool_name: str | None = None
    status: str = "pending"
    risk_level: RiskLevel = RiskLevel.R0
    result: str | None = None


class TaskState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    status: TaskStatus = TaskStatus.PENDING
    prompt: str
    plan: list[TaskPlanStep] = Field(default_factory=list)
    current_step: int = 0
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ApprovalRequest(BaseModel):
    task_id: str
    step_id: int
    approved: bool
    reason: str | None = None
