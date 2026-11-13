"""Example Zevon Extension. Copy this folder to make your own. See docs/plugin-guide.md."""
from datetime import datetime


def register(registry):
    @registry.tool("hello_time", "Return the current local time (example extension).", risk="read")
    def hello_time():
        return datetime.now().isoformat(timespec="seconds")
