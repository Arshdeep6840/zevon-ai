def load_all():
    """Import integrations so they register their tools. Add new connectors here (or in plugins/)."""
    from .system import filesystem  # noqa: F401
    from .google import gmail
    gmail.register()
