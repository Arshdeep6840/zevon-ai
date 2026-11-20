"""Permission Broker and Audit Logger for Zevon Tool Execution."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.shared_schemas.models import RiskLevel


class SecurityViolationError(Exception):
    """Raised when a tool violates sandbox boundaries or permission scopes."""


class ApprovalRequiredError(Exception):
    """Raised when an R2 or R3 action requires explicit human confirmation."""


class AuditRecord:
    def __init__(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        risk_level: RiskLevel,
        approved: bool = True,
        result: Any = None,
        is_error: bool = False,
    ):
        self.tool_name = tool_name
        self.arguments = arguments
        self.risk_level = risk_level
        self.approved = approved
        self.result = str(result)[:500] if result is not None else None
        self.is_error = is_error
        self.timestamp = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "risk_level": self.risk_level.value,
            "approved": self.approved,
            "result": self.result,
            "is_error": self.is_error,
            "timestamp": self.timestamp,
        }


class PermissionBroker:
    """
    Enforces risk level policies and workspace boundaries:
    - R0: Read-only -> automatic execution.
    - R1: Reversible local change -> auto within workspace or preview.
    - R2: Destructive/external -> require human approval.
    - R3: High impact/security -> require human approval or disabled.
    """

    def __init__(self, allowed_workspaces: list[str] | None = None):
        self.allowed_workspaces = [
            Path(p).resolve()
            for p in (allowed_workspaces or [Path.cwd()])
        ]
        self._audit_log: list[AuditRecord] = []

    @property
    def audit_log(self) -> list[dict[str, Any]]:
        return [record.to_dict() for record in self._audit_log]

    def add_allowed_workspace(self, path: str | Path) -> None:
        p = Path(path).resolve()
        if p not in self.allowed_workspaces:
            self.allowed_workspaces.append(p)

    def validate_file_path(self, target_path: str | Path) -> Path:
        """Verify target path is safely within an authorized workspace."""
        resolved = Path(target_path).resolve()
        for ws in self.allowed_workspaces:
            try:
                resolved.relative_to(ws)
                return resolved
            except ValueError:
                continue

        # Check if the target is within the workspace root
        raise SecurityViolationError(
            f"Path '{target_path}' is outside approved workspace directories: "
            f"{[str(w) for w in self.allowed_workspaces]}"
        )

    def check_permission(
        self,
        tool_name: str,
        risk_level: RiskLevel,
        arguments: dict[str, Any],
        is_user_approved: bool = False,
    ) -> bool:
        """Check whether tool call is authorized to execute."""
        # R0 actions run automatically
        if risk_level == RiskLevel.R0:
            return True

        # R1 actions run if within workspace
        if risk_level == RiskLevel.R1:
            if "path" in arguments:
                self.validate_file_path(arguments["path"])
            return True

        # R2 actions require explicit user approval
        if risk_level == RiskLevel.R2:
            if not is_user_approved:
                raise ApprovalRequiredError(
                    f"Action '{tool_name}' is classified as Risk Level R2 (Destructive/External) "
                    "and requires explicit user approval."
                )
            return True

        # R3 actions require explicit user approval
        if risk_level == RiskLevel.R3:
            if not is_user_approved:
                raise ApprovalRequiredError(
                    f"Action '{tool_name}' is classified as Risk Level R3 (Critical Impact) "
                    "and requires explicit user approval."
                )
            return True

        return False

    def log_action(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        risk_level: RiskLevel,
        approved: bool = True,
        result: Any = None,
        is_error: bool = False,
    ) -> None:
        record = AuditRecord(
            tool_name=tool_name,
            arguments=arguments,
            risk_level=risk_level,
            approved=approved,
            result=result,
            is_error=is_error,
        )
        self._audit_log.append(record)
        # Cap memory audit log to last 1000 events
        if len(self._audit_log) > 1000:
            self._audit_log.pop(0)
