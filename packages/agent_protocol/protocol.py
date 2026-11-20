"""Standardized Agent Calling API and JSON-RPC contracts for Zevon."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
import uuid


class AgentEventType(str, Enum):
    PROGRESS = "progress"
    THINKING = "thinking"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    MESSAGE = "message"
    ARTIFACT = "artifact"
    ERROR = "error"
    DONE = "done"


class ToolCallDefinition(BaseModel):
    call_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ToolResultDefinition(BaseModel):
    call_id: str
    tool_name: str
    output: Any
    is_error: bool = False


class AgentTaskRequest(BaseModel):
    """Payload to invoke a specialized sub-agent."""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    target_agent: str = "orchestrator"  # e.g., 'coder', 'researcher', 'general'
    instruction: str
    context: Dict[str, Any] = Field(default_factory=dict)
    allowed_tools: Optional[List[str]] = None
    stream_events: bool = True


class AgentEvent(BaseModel):
    """Real-time event emitted during agent task execution."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    event_type: AgentEventType
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentTaskResponse(BaseModel):
    """Final output from an agent execution."""
    task_id: str
    agent_name: str
    status: str = "success"  # success, failed, cancelled
    result_text: str
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    total_steps: int = 0
    error_message: Optional[str] = None


class AgentRPCRequest(BaseModel):
    """JSON-RPC 2.0 wrapper for cross-runtime agent calling."""
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)
    id: Union[str, int] = Field(default_factory=lambda: str(uuid.uuid4()))


class AgentRPCResponse(BaseModel):
    """JSON-RPC 2.0 response wrapper."""
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Union[str, int]
