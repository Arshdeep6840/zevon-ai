"""Tool Gateway and Execution API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.api.dependencies import get_repository, get_tool_registry
from services.memory.repository import MemoryRepository
from services.tools.permissions import ApprovalRequiredError, SecurityViolationError
from services.tools.registry import ToolRegistry

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


class ToolExecuteRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    is_approved: bool = False


class ToolDefinitionResponse(BaseModel):
    name: str
    description: str
    risk_level: str
    parameters: dict[str, Any]


@router.get("", response_model=list[ToolDefinitionResponse])
async def list_tools(
    tool_registry: ToolRegistry = Depends(get_tool_registry),
):
    """List all registered tools, their risk levels, and parameter schemas."""
    return [
        ToolDefinitionResponse(
            name=tool.name,
            description=tool.description,
            risk_level=tool.risk_level.value,
            parameters=tool.parameters,
        )
        for tool in tool_registry.list_tools()
    ]


@router.post("/execute")
async def execute_tool(
    req: ToolExecuteRequest,
    tool_registry: ToolRegistry = Depends(get_tool_registry),
    repo: MemoryRepository = Depends(get_repository),
):
    """Execute a tool through the security policy broker and audit logger."""
    context = {"repository": repo}
    try:
        res = await tool_registry.execute_tool(
            name=req.name,
            arguments=req.arguments,
            is_user_approved=req.is_approved,
            context=context,
        )
        return {"status": "success", "result": res}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ApprovalRequiredError as e:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "approval_required",
                "message": str(e),
                "tool_name": req.name,
                "arguments": req.arguments,
            },
        )
    except SecurityViolationError as e:
        raise HTTPException(status_code=400, detail={"error": "security_violation", "message": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "execution_failed", "message": str(e)})


@router.get("/audit")
async def get_audit_trail(
    tool_registry: ToolRegistry = Depends(get_tool_registry),
):
    """Retrieve the in-memory audit log of executed tool calls."""
    return tool_registry.permission_broker.audit_log
