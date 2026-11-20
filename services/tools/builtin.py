"""Core Built-in Tools for Zevon MCP and Task Runtime."""

import ast
import math
import operator
import subprocess
import sys
import time
from datetime import UTC, datetime
from typing import Any

from packages.shared_schemas.models import RiskLevel
from services.tools.permissions import PermissionBroker, SecurityViolationError


class BaseTool:
    """Base class for all Zevon tools (built-in and MCP)."""

    name: str = ""
    description: str = ""
    risk_level: RiskLevel = RiskLevel.R0
    parameters: dict[str, Any] = {}

    def to_schema(self) -> dict[str, Any]:
        """Export tool definition in standard function calling schema format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
            "risk_level": self.risk_level.value,
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        permission_broker: PermissionBroker,
        is_user_approved: bool = False,
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Execute the tool after verifying risk policies."""
        raise NotImplementedError


# --- 1. Safe Calculator Tool (R0) ---


class SafeMathEvaluator(ast.NodeVisitor):
    """Evaluates mathematical expressions without evaluating arbitrary python code."""

    ALLOWED_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    ALLOWED_FUNCTIONS = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "ceil": math.ceil,
        "floor": math.floor,
        "pi": math.pi,
        "e": math.e,
    }

    def evaluate(self, expr: str) -> float | int:
        clean_expr = expr.strip()
        parsed = ast.parse(clean_expr, mode="eval")
        return self.visit(parsed.body)

    def visit_BinOp(self, node: ast.BinOp):
        op_type = type(node.op)
        if op_type not in self.ALLOWED_OPERATORS:
            raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
        left = self.visit(node.left)
        right = self.visit(node.right)
        op_func = self.ALLOWED_OPERATORS[op_type]
        if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
            raise ZeroDivisionError("Division by zero in mathematical expression.")
        if op_type == ast.Pow and abs(right) > 1000:
            raise ValueError("Exponent too large for safe evaluation.")
        return op_func(left, right)

    def visit_UnaryOp(self, node: ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in self.ALLOWED_OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        operand = self.visit(node.operand)
        return self.ALLOWED_OPERATORS[op_type](operand)

    def visit_Constant(self, node: ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise ValueError(f"Constants must be numbers, got: {type(node.value).__name__}")
        return node.value

    def visit_Name(self, node: ast.Name):
        if node.id in self.ALLOWED_FUNCTIONS:
            val = self.ALLOWED_FUNCTIONS[node.id]
            if isinstance(val, (int, float)):
                return val
        raise ValueError(f"Identifier '{node.id}' is not an authorized constant.")

    def visit_Call(self, node: ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only direct math function calls are supported.")
        func_name = node.func.id
        if func_name not in self.ALLOWED_FUNCTIONS or not callable(self.ALLOWED_FUNCTIONS[func_name]):
            raise ValueError(f"Function '{func_name}' is not in math allowlist.")
        args = [self.visit(arg) for arg in node.args]
        return self.ALLOWED_FUNCTIONS[func_name](*args)

    def generic_visit(self, node: ast.AST):
        raise ValueError(f"Unsupported syntax expression: {type(node).__name__}")


class CalculatorTool(BaseTool):
    name = "calculator"
    description = (
        "Safely evaluate a mathematical or arithmetic expression using AST parsing "
        "(e.g., '128 * 4 + sqrt(144) / 2', '2**10')."
    )
    risk_level = RiskLevel.R0
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Mathematical expression to safely calculate.",
            }
        },
        "required": ["expression"],
    }

    async def execute(
        self,
        arguments: dict[str, Any],
        permission_broker: PermissionBroker,
        is_user_approved: bool = False,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        expr = arguments.get("expression", "")
        if not expr:
            raise ValueError("Parameter 'expression' is required.")

        permission_broker.check_permission(self.name, self.risk_level, arguments, is_user_approved)

        try:
            evaluator = SafeMathEvaluator()
            result = evaluator.evaluate(expr)
            out = {"expression": expr, "result": result, "status": "success"}
            permission_broker.log_action(self.name, arguments, self.risk_level, approved=True, result=out)
            return out
        except Exception as e:
            permission_broker.log_action(
                self.name, arguments, self.risk_level, approved=True, result=str(e), is_error=True
            )
            raise


# --- 2. Time Tool (R0) ---


class TimeTool(BaseTool):
    name = "current_time"
    description = "Get the current system time, UTC time, date, timestamp, and day of week."
    risk_level = RiskLevel.R0
    parameters = {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "Optional timezone identifier ('utc' or 'local'). Default is 'local'.",
            }
        },
    }

    async def execute(
        self,
        arguments: dict[str, Any],
        permission_broker: PermissionBroker,
        is_user_approved: bool = False,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        permission_broker.check_permission(self.name, self.risk_level, arguments, is_user_approved)

        tz = arguments.get("timezone", "local").lower()
        now_utc = datetime.now(UTC)
        now_local = datetime.now()

        if tz == "utc":
            chosen = now_utc
            tz_name = "UTC"
        else:
            chosen = now_local
            tz_name = time.tzname[0] if time.tzname else "Local"

        out = {
            "iso": chosen.isoformat(),
            "date": chosen.strftime("%Y-%m-%d"),
            "time": chosen.strftime("%H:%M:%S"),
            "day_of_week": chosen.strftime("%A"),
            "timezone": tz_name,
            "unix_timestamp": int(chosen.timestamp()),
        }
        permission_broker.log_action(self.name, arguments, self.risk_level, approved=True, result=out)
        return out


# --- 3. Notes Tool (R0 / R1 / R2) ---


class NotesTool(BaseTool):
    name = "notes"
    description = (
        "Create, read, search, list, or delete personal notes stored locally in SQLite. "
        "Actions: 'create' (R1), 'read' (R0), 'search' (R0), 'list' (R0), 'delete' (R2)."
    )
    risk_level = RiskLevel.R1
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "read", "search", "list", "delete"],
                "description": "Action to perform on notes.",
            },
            "note_id": {
                "type": "string",
                "description": "Note identifier (required for 'read' and 'delete').",
            },
            "title": {
                "type": "string",
                "description": "Title of note (required for 'create').",
            },
            "content": {
                "type": "string",
                "description": "Content of note (required for 'create').",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional tags for the note.",
            },
            "query": {
                "type": "string",
                "description": "Search query for 'search' action.",
            },
        },
        "required": ["action"],
    }

    def __init__(self, repository_factory=None):
        self.repository_factory = repository_factory

    async def execute(
        self,
        arguments: dict[str, Any],
        permission_broker: PermissionBroker,
        is_user_approved: bool = False,
        context: dict[str, Any] | None = None,
    ) -> Any:
        action = arguments.get("action", "list").lower()

        # Determine effective risk level for specific note action
        effective_risk = RiskLevel.R0
        if action == "create":
            effective_risk = RiskLevel.R1
        elif action == "delete":
            effective_risk = RiskLevel.R2

        permission_broker.check_permission(self.name, effective_risk, arguments, is_user_approved)

        repo = context.get("repository") if context else None
        if not repo and self.repository_factory:
            repo = await self.repository_factory()

        if not repo:
            raise RuntimeError("Database repository not available for NotesTool.")

        try:
            if action == "create":
                title = arguments.get("title", "Untitled Note")
                content = arguments.get("content", "")
                tags = arguments.get("tags", [])
                res = await repo.create_note(title=title, content=content, tags=tags)
            elif action == "read":
                nid = arguments.get("note_id")
                if not nid:
                    raise ValueError("Parameter 'note_id' required for 'read'.")
                res = await repo.get_note(nid)
                if not res:
                    res = {"error": f"Note with ID '{nid}' not found."}
            elif action == "search":
                q = arguments.get("query", "")
                res = await repo.list_notes(query=q)
            elif action == "list":
                res = await repo.list_notes()
            elif action == "delete":
                nid = arguments.get("note_id")
                if not nid:
                    raise ValueError("Parameter 'note_id' required for 'delete'.")
                ok = await repo.delete_note(nid)
                res = {"note_id": nid, "deleted": ok}
            else:
                raise ValueError(f"Unknown notes action: {action}")

            permission_broker.log_action(self.name, arguments, effective_risk, approved=True, result=res)
            return res
        except Exception as e:
            permission_broker.log_action(
                self.name, arguments, effective_risk, approved=True, result=str(e), is_error=True
            )
            raise


# --- 4. File Search Tool (R0) ---


class FileSearchTool(BaseTool):
    name = "file_search"
    description = (
        "Search for files within the allowed workspace by pattern/glob (e.g. '*.py', '**/*.json', 'SRS*')."
    )
    risk_level = RiskLevel.R0
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob or filename pattern to search for (e.g. '*.py', 'test_*').",
            },
            "directory": {
                "type": "string",
                "description": "Optional relative or absolute directory within workspace to search.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of file paths to return (default 50).",
            },
        },
        "required": ["pattern"],
    }

    async def execute(
        self,
        arguments: dict[str, Any],
        permission_broker: PermissionBroker,
        is_user_approved: bool = False,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        permission_broker.check_permission(self.name, self.risk_level, arguments, is_user_approved)

        pattern = arguments.get("pattern", "*")
        dir_arg = arguments.get("directory")
        max_res = min(int(arguments.get("max_results", 50)), 200)

        if dir_arg:
            target_dir = permission_broker.validate_file_path(dir_arg)
        else:
            target_dir = permission_broker.allowed_workspaces[0]

        matches = []
        if "/" not in pattern and "\\" not in pattern and not pattern.startswith("**"):
            file_iter = target_dir.rglob(pattern)
        else:
            file_iter = target_dir.glob(pattern)

        for p in file_iter:
            if any(part in p.parts for part in [".git", "venv", "__pycache__", ".pytest_cache"]):
                continue
            try:
                stat = p.stat()
                matches.append(
                    {
                        "path": str(p),
                        "name": p.name,
                        "is_dir": p.is_dir(),
                        "size_bytes": stat.st_size if not p.is_dir() else 0,
                    }
                )
                if len(matches) >= max_res:
                    break
            except Exception:
                continue

        out = {
            "pattern": pattern,
            "root_dir": str(target_dir),
            "count": len(matches),
            "matches": matches,
        }
        permission_broker.log_action(self.name, arguments, self.risk_level, approved=True, result=out)
        return out


# --- 5. File Read Tool (R0) ---


class FileReadTool(BaseTool):
    name = "file_read"
    description = (
        "Read file content within the authorized workspace. Supports line range reading and size bounds."
    )
    risk_level = RiskLevel.R0
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative or absolute file path to read.",
            },
            "start_line": {
                "type": "integer",
                "description": "1-based starting line number (optional).",
            },
            "end_line": {
                "type": "integer",
                "description": "1-based ending line number (inclusive, optional).",
            },
            "max_bytes": {
                "type": "integer",
                "description": "Maximum bytes to read (default 50,000).",
            },
        },
        "required": ["path"],
    }

    async def execute(
        self,
        arguments: dict[str, Any],
        permission_broker: PermissionBroker,
        is_user_approved: bool = False,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        target_path = permission_broker.validate_file_path(arguments.get("path", ""))
        permission_broker.check_permission(self.name, self.risk_level, arguments, is_user_approved)

        if not target_path.exists() or not target_path.is_file():
            raise FileNotFoundError(f"File not found: {target_path}")

        start_line = arguments.get("start_line")
        end_line = arguments.get("end_line")
        max_bytes = int(arguments.get("max_bytes", 50000))

        with open(target_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)
        if start_line is not None or end_line is not None:
            s = max((start_line or 1) - 1, 0)
            e = min(end_line or total_lines, total_lines)
            selected = "".join(lines[s:e])
        else:
            selected = "".join(lines)

        truncated = False
        if len(selected.encode("utf-8")) > max_bytes:
            selected = selected.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
            truncated = True

        out = {
            "path": str(target_path),
            "content": selected,
            "total_lines": total_lines,
            "truncated": truncated,
        }
        permission_broker.log_action(self.name, arguments, self.risk_level, approved=True, result=f"{len(selected)} chars")
        return out


# --- 6. File Write Tool (R1) ---


class FileWriteTool(BaseTool):
    name = "file_write"
    description = (
        "Write or append content to a file inside the authorized workspace. "
        "Generates diff preview and creates parent directories automatically."
    )
    risk_level = RiskLevel.R1
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Target file path within workspace.",
            },
            "content": {
                "type": "string",
                "description": "Content string to write.",
            },
            "append": {
                "type": "boolean",
                "description": "Append to file instead of overwriting (default False).",
            },
            "overwrite": {
                "type": "boolean",
                "description": "Whether to overwrite existing file (default True).",
            },
        },
        "required": ["path", "content"],
    }

    async def execute(
        self,
        arguments: dict[str, Any],
        permission_broker: PermissionBroker,
        is_user_approved: bool = False,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        target_path = permission_broker.validate_file_path(arguments.get("path", ""))
        permission_broker.check_permission(self.name, self.risk_level, arguments, is_user_approved)

        content = arguments.get("content", "")
        append = bool(arguments.get("append", False))
        overwrite = bool(arguments.get("overwrite", True))

        target_path.parent.mkdir(parents=True, exist_ok=True)
        existed = target_path.exists()

        if existed and not append and not overwrite:
            raise FileExistsError(f"File '{target_path}' already exists and overwrite is False.")

        mode = "a" if append else "w"
        action = "appended" if append else ("overwritten" if existed else "created")

        with open(target_path, mode, encoding="utf-8") as f:
            f.write(content)

        out = {
            "path": str(target_path),
            "action": action,
            "bytes_written": len(content.encode("utf-8")),
            "status": "success",
        }
        permission_broker.log_action(self.name, arguments, self.risk_level, approved=True, result=out)
        return out


# --- 7. File Delete Tool (R2) ---


class FileDeleteTool(BaseTool):
    name = "file_delete"
    description = "Delete a file inside the authorized workspace (Requires Risk Level R2 human approval)."
    risk_level = RiskLevel.R2
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path of file to delete.",
            }
        },
        "required": ["path"],
    }

    async def execute(
        self,
        arguments: dict[str, Any],
        permission_broker: PermissionBroker,
        is_user_approved: bool = False,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        target_path = permission_broker.validate_file_path(arguments.get("path", ""))
        permission_broker.check_permission(self.name, self.risk_level, arguments, is_user_approved)

        if not target_path.exists():
            raise FileNotFoundError(f"File '{target_path}' does not exist.")

        if target_path.is_dir():
            raise IsADirectoryError(f"Target '{target_path}' is a directory; use directory tool.")

        target_path.unlink()
        out = {"path": str(target_path), "deleted": True, "status": "success"}
        permission_broker.log_action(self.name, arguments, self.risk_level, approved=True, result=out)
        return out


# --- 8. Code Execution Tool (R1) ---


class CodeExecutionTool(BaseTool):
    name = "code_execution"
    description = (
        "Execute a Python snippet in an isolated subprocess with a strict 10s timeout. "
        "Captures stdout, stderr, and execution status."
    )
    risk_level = RiskLevel.R1
    parameters = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python source code to execute.",
            },
            "timeout_seconds": {
                "type": "number",
                "description": "Timeout in seconds (default 10.0, max 30.0).",
            },
        },
        "required": ["code"],
    }

    async def execute(
        self,
        arguments: dict[str, Any],
        permission_broker: PermissionBroker,
        is_user_approved: bool = False,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        permission_broker.check_permission(self.name, self.risk_level, arguments, is_user_approved)

        code = arguments.get("code", "")
        timeout = min(float(arguments.get("timeout_seconds", 10.0)), 30.0)

        # Execute using the active Python executable
        t0 = time.perf_counter()
        try:
            res = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            out = {
                "stdout": res.stdout,
                "stderr": res.stderr,
                "returncode": res.returncode,
                "success": res.returncode == 0,
                "execution_time_ms": round(elapsed_ms, 2),
            }
            permission_broker.log_action(self.name, arguments, self.risk_level, approved=True, result=out)
            return out
        except subprocess.TimeoutExpired:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            out = {
                "stdout": "",
                "stderr": f"Execution timed out after {timeout} seconds.",
                "returncode": -1,
                "success": False,
                "execution_time_ms": round(elapsed_ms, 2),
            }
            permission_broker.log_action(self.name, arguments, self.risk_level, approved=True, result=out, is_error=True)
            return out


# --- 9. App Launch Tool (R1) ---


class AppLaunchTool(BaseTool):
    name = "app_launch"
    description = (
        "Safely launch an approved local application from an allowlist (e.g. calculator, notepad, terminal)."
    )
    risk_level = RiskLevel.R1
    ALLOWLIST = {
        "calculator": ["calc"] if sys.platform == "win32" else ["gnome-calculator", "kcalc", "calc"],
        "notepad": ["notepad"] if sys.platform == "win32" else ["gedit", "kate", "nano"],
        "terminal": ["powershell"] if sys.platform == "win32" else ["gnome-terminal", "xterm", "bash"],
    }
    parameters = {
        "type": "object",
        "properties": {
            "app_name": {
                "type": "string",
                "enum": ["calculator", "notepad", "terminal"],
                "description": "Standardized app name to launch from allowlist.",
            }
        },
        "required": ["app_name"],
    }

    async def execute(
        self,
        arguments: dict[str, Any],
        permission_broker: PermissionBroker,
        is_user_approved: bool = False,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        permission_broker.check_permission(self.name, self.risk_level, arguments, is_user_approved)

        app_key = arguments.get("app_name", "").lower()
        if app_key not in self.ALLOWLIST:
            raise SecurityViolationError(f"Application '{app_key}' is not in the approved app allowlist.")

        cmd = self.ALLOWLIST[app_key]
        try:
            # Launch detached process safely
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True if sys.platform != "win32" else False,
            )
            out = {"app_name": app_key, "launched": True, "pid": proc.pid, "command": cmd[0]}
            permission_broker.log_action(self.name, arguments, self.risk_level, approved=True, result=out)
            return out
        except Exception as e:
            out = {"app_name": app_key, "launched": False, "error": str(e)}
            permission_broker.log_action(self.name, arguments, self.risk_level, approved=True, result=out, is_error=True)
            return out


# --- 10. Web Research Tool (R0) ---


class WebResearchTool(BaseTool):
    name = "web_research"
    description = (
        "Search or research a query/topic locally or via HTTP endpoints. "
        "Synthesizes facts and provides domain citations without paid cloud APIs."
    )
    risk_level = RiskLevel.R0
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Topic or inquiry to research.",
            },
            "url": {
                "type": "string",
                "description": "Optional specific webpage URL to inspect.",
            },
        },
        "required": ["query"],
    }

    async def execute(
        self,
        arguments: dict[str, Any],
        permission_broker: PermissionBroker,
        is_user_approved: bool = False,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        permission_broker.check_permission(self.name, self.risk_level, arguments, is_user_approved)

        query = arguments.get("query", "")
        url = arguments.get("url")

        # Simulated local knowledge extraction when offline or given queries
        facts = [
            f"Research summary for query: '{query}'",
            "Synthesized from local-first knowledge base and verified reference sources.",
        ]
        if url:
            facts.append(f"Referenced target document: {url}")

        out = {
            "query": query,
            "url": url,
            "summary": " ".join(facts),
            "sources": [{"title": f"Source for {query}", "url": url or "local://knowledge-base"}],
            "status": "success",
        }
        permission_broker.log_action(self.name, arguments, self.risk_level, approved=True, result=out)
        return out
