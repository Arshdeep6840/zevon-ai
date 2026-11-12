"""Filesystem tools. Everything is sandboxed to JARVIS_ALLOWED_FOLDERS (deny by default)."""
import hashlib
import shutil
from collections import defaultdict
from pathlib import Path

from ...config import settings
from ...core.tools import registry

CATEGORIES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".odt", ".rtf", ".ppt", ".pptx"},
    "Spreadsheets": {".xls", ".xlsx", ".csv"},
    "Archives": {".zip", ".tar", ".gz", ".rar", ".7z"},
    "Audio": {".mp3", ".wav", ".flac", ".m4a"},
    "Video": {".mp4", ".mkv", ".mov", ".avi"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".json", ".ipynb"},
    "Installers": {".exe", ".msi", ".dmg", ".deb", ".apk"},
}


def safe_path(path: str) -> Path:
    p = Path(path).expanduser().resolve()
    for root in settings.allowed_folders:
        r = Path(root).expanduser().resolve()
        if p == r or r in p.parents:
            return p
    raise PermissionError(f"{p} is outside the authorized folders. Set JARVIS_ALLOWED_FOLDERS.")


def _category(p: Path) -> str:
    ext = p.suffix.lower()
    return next((c for c, exts in CATEGORIES.items() if ext in exts), "Other")


def _plan(folder: Path) -> list[dict]:
    return [{"from": str(f), "to": str(folder / _category(f) / f.name)}
            for f in sorted(folder.iterdir()) if f.is_file() and not f.name.startswith(".")]


PATH = {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}


@registry.tool("fs_list_dir", "List files and folders in an authorized directory.", PATH, risk="read")
def list_dir(path: str):
    p = safe_path(path)
    return "\n".join(f"{'[dir] ' if c.is_dir() else ''}{c.name}" for c in sorted(p.iterdir())) or "(empty)"


@registry.tool("fs_read_file", "Read a text file from an authorized folder (first 4000 chars).", PATH, risk="read")
def read_file(path: str):
    return safe_path(path).read_text(errors="replace")[:4000]


@registry.tool("fs_find_duplicates", "Find duplicate files (same content) inside an authorized folder.", PATH, risk="read")
def find_duplicates(path: str):
    by_size = defaultdict(list)
    for f in list(safe_path(path).rglob("*"))[:5000]:
        if f.is_file():
            by_size[f.stat().st_size].append(f)
    groups = defaultdict(list)
    for files in by_size.values():
        if len(files) > 1:
            for f in files:
                groups[hashlib.sha256(f.read_bytes()).hexdigest()].append(str(f))
    dups = [g for g in groups.values() if len(g) > 1]
    return "\n".join(" == ".join(g) for g in dups) or "No duplicates found."


@registry.tool("fs_plan_organize", "Preview how files in a folder would be sorted into type subfolders (no changes made).",
               PATH, risk="read")
def plan_organize(path: str):
    plan = _plan(safe_path(path))
    return "\n".join(f"{m['from']} -> {m['to']}" for m in plan) or "Nothing to organize."


@registry.tool("fs_apply_organize", "Actually move files into type subfolders. Requires user approval.", PATH, risk="sensitive")
def apply_organize(path: str):
    moved = 0
    for m in _plan(safe_path(path)):
        dst = Path(m["to"])
        dst.parent.mkdir(exist_ok=True)
        n = 1
        while dst.exists():
            dst = dst.with_name(f"{dst.stem}_{n}{dst.suffix}")
            n += 1
        shutil.move(m["from"], dst)
        moved += 1
    return f"Moved {moved} files."


@registry.tool("fs_delete_file", "Delete a file. Requires user approval.", PATH, risk="sensitive")
def delete_file(path: str):
    p = safe_path(path)
    p.unlink()
    return f"Deleted {p}"
