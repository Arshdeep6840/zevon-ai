"""Data contracts and schemas for Zevon."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


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
    tool_calls: Optional[List[Dict[str, Any]]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "New Conversation"
    profile: str = "personal"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ModelCard(BaseModel):
    id: str
    name: str
    provider: str
    parameter_size: str = "compact"
    quantization: Optional[str] = None
    context_length: int = 4096
    is_active: bool = False
    is_installed: bool = True
    description: Optional[str] = None


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    model_id: Optional[str] = None
    stream: bool = True
    temperature: float = 0.7


class ChatChunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    delta: str
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


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
    tool_name: Optional[str] = None
    status: str = "pending"
    risk_level: RiskLevel = RiskLevel.R0
    result: Optional[str] = None


class TaskState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    status: TaskStatus = TaskStatus.PENDING
    prompt: str
    plan: List[TaskPlanStep] = Field(default_factory=list)
    current_step: int = 0
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ApprovalRequest(BaseModel):
    task_id: str
    step_id: int
    approved: bool
    reason: Optional[str] = None
