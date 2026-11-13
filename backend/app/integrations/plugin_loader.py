"""Zevon Extensions loader: plugins/<name>/plugin.py (or plugins/<name>.py) exposing register(registry)."""
import importlib.util
from pathlib import Path

from ..config import settings


def load_plugins(registry, store=None) -> list[str]:
    root, loaded = Path(settings.plugins_dir), []
    if not root.exists():
        return loaded
    for entry in sorted(root.iterdir()):
        if entry.name.startswith(("_", ".")):
            continue
        target = entry / "plugin.py" if entry.is_dir() else entry
        if target.suffix != ".py" or not target.exists():
            continue
        try:
            spec = importlib.util.spec_from_file_location(f"zevon_ext_{entry.stem}", target)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "register"):
                mod.register(registry)
                loaded.append(entry.stem)
        except Exception as e:
            if store:
                store.audit("extensions", entry.name, str(e)[:300], "load failed")
    return loaded
