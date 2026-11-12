"""The AI suggests actions; this policy decides whether they are allowed."""
from enum import Enum


class Decision(str, Enum):
    ALLOW = "allow"
    APPROVE = "approve"   # queue for human approval
    DENY = "deny"


DEFAULT_BY_RISK = {
    "read": Decision.ALLOW,
    "safe_write": Decision.ALLOW,      # e.g. create email draft
    "sensitive": Decision.APPROVE,     # send email, delete files, move files
    "blocked": Decision.DENY,
}


class PermissionPolicy:
    def __init__(self, overrides: dict[str, Decision] | None = None):
        self.overrides = overrides or {}
        self.kill_switch = False

    def decide(self, tool) -> Decision:
        if self.kill_switch:
            return Decision.DENY
        if tool.name in self.overrides:
            return self.overrides[tool.name]
        return DEFAULT_BY_RISK[tool.risk]
