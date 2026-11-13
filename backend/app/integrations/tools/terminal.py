"""Restricted terminal: allowlisted programs only, no shell, no pipes/redirects, 15s timeout.
Extend with ZEVON_TERMINAL_EXTRA=prog1,prog2 (whole programs; use with care)."""
import re
import shlex
import subprocess
import tempfile

from ...config import settings
from ...core.tools import registry
from ..system.filesystem import safe_path

ALLOW: dict[str, set | None] = {
    "ls": None, "pwd": None, "date": None, "whoami": None, "uname": None, "df": None, "du": None,
    "free": None, "uptime": None, "hostname": None, "nvidia-smi": None,
    "git": {"status", "log", "diff", "branch", "remote", "show"},
    "python": {"--version", "-V"}, "python3": {"--version", "-V"},
    "pip": {"list", "--version"}, "node": {"--version"}, "ollama": {"list", "ps"},
}
FORBIDDEN_CHARS = set(";|&><`$\n")
BAD_GIT_ARGS = re.compile(r"^(--output|--ext-diff|--textconv|-c$|--exec|--upload-pack|--git-dir|--work-tree)")


def run_command(command: str) -> str:
    if any(c in command for c in FORBIDDEN_CHARS):
        raise PermissionError("Shell operators (; | & > < ` $) are not allowed.")
    argv = shlex.split(command)
    if not argv:
        raise ValueError("Empty command.")
    prog = argv[0]
    allowed = dict(ALLOW)
    allowed.update({p: None for p in settings.terminal_extra})
    if prog not in allowed:
        raise PermissionError(f"'{prog}' is not on the terminal allowlist.")
    subs = allowed[prog]
    if subs is not None and (len(argv) < 2 or argv[1] not in subs):
        raise PermissionError(f"Only these subcommands are allowed for {prog}: {sorted(subs)}")
    for a in argv[1:]:
        if prog == "git" and BAD_GIT_ARGS.match(a):
            raise PermissionError(f"Argument {a} is not allowed.")
        if not a.startswith("-") and ("/" in a or ".." in a or "\\" in a):
            safe_path(a)  # any path argument must be inside authorized folders
    cwd = settings.allowed_folders[0] if settings.allowed_folders else tempfile.gettempdir()
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=15)
    return ((p.stdout or "") + (p.stderr or ""))[:4000] or f"(exit code {p.returncode}, no output)"


registry.tool("terminal_run", "Run a safe, allowlisted read-only shell command (ls, pwd, df, git status, nvidia-smi...). "
              "No pipes or redirects.", {"type": "object", "properties": {"command": {"type": "string"}},
                                          "required": ["command"]}, risk="read")(run_command)
