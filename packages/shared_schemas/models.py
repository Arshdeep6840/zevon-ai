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
