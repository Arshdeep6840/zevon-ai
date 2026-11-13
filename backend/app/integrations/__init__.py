from ..config import settings


def load_all():
    """Import built-in Zevon Extensions so they register their tools."""
    from .system import filesystem  # noqa: F401
    from .tools import browser, terminal  # noqa: F401
    if settings.terminal_ask.lower() in ("on", "1", "true", "yes"):
        terminal.register_ask_mode()
    from . import google
    google.register_all()
    if settings.notion_token:
        from .productivity import notion
        notion.register()
    if settings.todoist_token:
        from .productivity import todoist
        todoist.register()
    if settings.slack_token:
        from .productivity import slack
        slack.register()
