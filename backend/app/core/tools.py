"""Tool registry. The LLM can only *request* tools registered here; permissions.py decides if they run."""
from dataclasses import dataclass
from typing import Callable

# risk levels: read | safe_write | sensitive | blocked
RISKS = ("read", "safe_write", "sensitive", "blocked")


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    risk: str
    func: Callable


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        assert tool.risk in RISKS, f"bad risk {tool.risk}"
        self._tools[tool.name] = tool

    def tool(self, name: str, description: str, parameters: dict | None = None, risk: str = "read"):
        def deco(fn):
            self.register(Tool(name, description,
                               parameters or {"type": "object", "properties": {}}, risk, fn))
            return fn
        return deco

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def specs(self) -> list[dict]:
        return [{"type": "function", "function": {"name": t.name, "description": t.description,
                                                   "parameters": t.parameters}} for t in self.all()]


registry = ToolRegistry()
