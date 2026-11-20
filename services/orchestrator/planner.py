"""Task Planner: Decomposes complex user requests into structured execution steps."""

import json
import re
from typing import Any

from packages.shared_schemas.models import RiskLevel, TaskPlanStep
from services.model_gateway.registry import ModelRegistry
from services.tools.registry import ToolRegistry


class TaskPlanner:
    """
    Analyzes user prompts, identifies goals and dependencies,
    and produces an ordered list of TaskPlanSteps with assigned tools and risk levels.
    """

    def __init__(self, tool_registry: ToolRegistry, model_gateway: ModelRegistry | None = None):
        self.tool_registry = tool_registry
        self.model_gateway = model_gateway

    async def plan(self, prompt: str, context: dict[str, Any] | None = None) -> list[TaskPlanStep]:
        """
        Generate execution plan for a user prompt.
        Attempts LLM-based planning if model available, falling back to rule-based decomposition.
        """
        if self.model_gateway:
            try:
                llm_plan = await self._plan_with_llm(prompt)
                if llm_plan:
                    return llm_plan
            except Exception:
                pass  # Fall back to heuristic decomposition

        return self._plan_heuristic(prompt)

    async def _plan_with_llm(self, prompt: str) -> list[TaskPlanStep] | None:
        """Attempt to decompose task using active local LLM."""
        provider = self.model_gateway.get_active_provider()
        tools_summary = [
            f"- {t.name} ({t.risk_level.value}): {t.description}"
            for t in self.tool_registry.list_tools()
        ]
        system_prompt = (
            "You are Zevon's Task Planning Engine. Decompose the user's request into 1 to 5 sequential execution steps.\n"
            f"Available tools:\n{chr(10).join(tools_summary)}\n\n"
            "Respond ONLY with a valid JSON array of objects with keys:\n"
            '  "title": str,\n'
            '  "tool_name": str or null,\n'
            '  "arguments": dict of arguments,\n'
            '  "risk_level": "R0", "R1", "R2", or "R3"\n'
        )
        response_text = ""
        async for chunk in provider.generate_stream(
            model_id="default",
            prompt=f"User request: {prompt}\nPlan steps:",
            system_prompt=system_prompt,
            temperature=0.1,
        ):
            response_text += chunk.delta

        # Extract JSON array
        match = re.search(r"\[\s*\{.*\}\s*\]", response_text, re.DOTALL)
        if match:
            raw_steps = json.loads(match.group(0))
            steps = []
            for i, s in enumerate(raw_steps, 1):
                tool = self.tool_registry.get_tool(s.get("tool_name", ""))
                risk = RiskLevel(s.get("risk_level", tool.risk_level.value if tool else "R0"))
                steps.append(
                    TaskPlanStep(
                        step_id=i,
                        title=s.get("title", f"Step {i}"),
                        tool_name=s.get("tool_name"),
                        arguments=s.get("arguments", {}),
                        risk_level=risk,
                        status="pending",
                    )
                )
            if steps:
                return steps
        return None

    def _plan_heuristic(self, prompt: str) -> list[TaskPlanStep]:
        """Heuristic planner decomposing common multi-step and single-step requests."""
        lower = prompt.lower().strip()
        steps: list[TaskPlanStep] = []

        # Check multi-step: "calculate ... and write/save to ..."
        if ("calculate" in lower or re.search(r"\d+[\s\+\-\*\/\^]+\d+", lower)) and (
            "write" in lower or "save" in lower
        ):
            # Extract expression
            calc_match = re.search(r"calculate\s+([^\s,;]+(?:\s*[\+\-\*\/]\s*[^\s,;]+)*)", prompt, re.I)
            expr = calc_match.group(1) if calc_match else "10 + 20"
            file_match = re.search(r"(?:to|file)\s+([a-zA-Z0-9_\-\.\/\\:]+\.[a-zA-Z0-9]+)", prompt, re.I)
            target_file = file_match.group(1) if file_match else "calc_result.txt"

            steps.append(
                TaskPlanStep(
                    step_id=1,
                    title=f"Calculate expression: {expr}",
                    tool_name="calculator",
                    arguments={"expression": expr},
                    risk_level=RiskLevel.R0,
                    status="pending",
                )
            )
            steps.append(
                TaskPlanStep(
                    step_id=2,
                    title=f"Save result to {target_file}",
                    tool_name="file_write",
                    arguments={"path": target_file, "content": "Calculated Result"},
                    risk_level=RiskLevel.R1,
                    status="pending",
                )
            )
            return steps

        # Check multi-step: "research ... and save note / save file"
        if ("research" in lower or "find out" in lower) and ("note" in lower or "save" in lower):
            topic = re.sub(r"(research|find out|and save.*)", "", prompt, flags=re.I).strip() or "General inquiry"
            steps.append(
                TaskPlanStep(
                    step_id=1,
                    title=f"Research topic: {topic}",
                    tool_name="web_research",
                    arguments={"query": topic},
                    risk_level=RiskLevel.R0,
                    status="pending",
                )
            )
            steps.append(
                TaskPlanStep(
                    step_id=2,
                    title=f"Record notes on {topic}",
                    tool_name="notes",
                    arguments={"action": "create", "title": f"Notes on {topic}", "content": f"Research on {topic}"},
                    risk_level=RiskLevel.R1,
                    status="pending",
                )
            )
            return steps

        # Single step detection:
        # Calculator
        if "calculate" in lower or re.search(r"^\s*[\d\(\)\.\s\+\-\*\/\^]+\s*$", prompt):
            expr_match = re.search(r"calculate\s+(.+)$", prompt, re.I)
            expr = expr_match.group(1).strip() if expr_match else prompt.strip()
            return [
                TaskPlanStep(
                    step_id=1,
                    title=f"Calculate: {expr}",
                    tool_name="calculator",
                    arguments={"expression": expr},
                    risk_level=RiskLevel.R0,
                    status="pending",
                )
            ]

        # Time
        if any(k in lower for k in ["what time", "current time", "what date", "today's date", "timestamp"]):
            return [
                TaskPlanStep(
                    step_id=1,
                    title="Retrieve current date and time",
                    tool_name="current_time",
                    arguments={"timezone": "local"},
                    risk_level=RiskLevel.R0,
                    status="pending",
                )
            ]

        # File search
        if any(k in lower for k in ["find file", "search file", "locate file", "list files"]):
            pattern_match = re.search(r"(\*\.[a-zA-Z0-9]+|[a-zA-Z0-9_\-\*]+\.[a-zA-Z0-9]+)", prompt)
            pattern = pattern_match.group(1) if pattern_match else "*"
            return [
                TaskPlanStep(
                    step_id=1,
                    title=f"Search files matching '{pattern}'",
                    tool_name="file_search",
                    arguments={"pattern": pattern},
                    risk_level=RiskLevel.R0,
                    status="pending",
                )
            ]

        # File read
        if any(k in lower for k in ["read file", "open file", "inspect file", "show content of"]):
            file_match = re.search(r"([a-zA-Z0-9_\-\.\/\\:]+\.[a-zA-Z0-9]+)", prompt)
            path = file_match.group(1) if file_match else "README.md"
            return [
                TaskPlanStep(
                    step_id=1,
                    title=f"Read file '{path}'",
                    tool_name="file_read",
                    arguments={"path": path},
                    risk_level=RiskLevel.R0,
                    status="pending",
                )
            ]

        # File delete (R2 action)
        if any(k in lower for k in ["delete file", "remove file", "erase file"]):
            file_match = re.search(r"([a-zA-Z0-9_\-\.\/\\:]+\.[a-zA-Z0-9]+)", prompt)
            path = file_match.group(1) if file_match else "temp.txt"
            return [
                TaskPlanStep(
                    step_id=1,
                    title=f"Delete file '{path}'",
                    tool_name="file_delete",
                    arguments={"path": path},
                    risk_level=RiskLevel.R2,
                    status="pending",
                )
            ]

        # File write
        if any(k in lower for k in ["write file", "create file", "save file"]):
            file_match = re.search(r"([a-zA-Z0-9_\-\.\/\\:]+\.[a-zA-Z0-9]+)", prompt)
            path = file_match.group(1) if file_match else "output.txt"
            return [
                TaskPlanStep(
                    step_id=1,
                    title=f"Write to file '{path}'",
                    tool_name="file_write",
                    arguments={"path": path, "content": "File created by Zevon."},
                    risk_level=RiskLevel.R1,
                    status="pending",
                )
            ]

        # Code execution
        if any(k in lower for k in ["run python", "execute code", "run code", "run script"]):
            return [
                TaskPlanStep(
                    step_id=1,
                    title="Execute Python snippet",
                    tool_name="code_execution",
                    arguments={"code": "print('Code executed successfully.')"},
                    risk_level=RiskLevel.R1,
                    status="pending",
                )
            ]

        # App launch
        if any(k in lower for k in ["launch", "open app", "start app"]):
            app = "calculator"
            for candidate in ["calculator", "notepad", "terminal"]:
                if candidate in lower:
                    app = candidate
                    break
            return [
                TaskPlanStep(
                    step_id=1,
                    title=f"Launch application '{app}'",
                    tool_name="app_launch",
                    arguments={"app_name": app},
                    risk_level=RiskLevel.R1,
                    status="pending",
                )
            ]

        # Notes
        if "note" in lower:
            action = "create" if any(w in lower for w in ["create", "add", "take", "write", "save"]) else "list"
            return [
                TaskPlanStep(
                    step_id=1,
                    title=f"Notes: {action}",
                    tool_name="notes",
                    arguments={"action": action, "title": prompt[:30], "content": prompt},
                    risk_level=RiskLevel.R1 if action == "create" else RiskLevel.R0,
                    status="pending",
                )
            ]

        # Default web research / synthesis
        return [
            TaskPlanStep(
                step_id=1,
                title=f"Research and answer: {prompt[:40]}",
                tool_name="web_research",
                arguments={"query": prompt},
                risk_level=RiskLevel.R0,
                status="pending",
            )
        ]
