from . import auth


def register_all():
    """Register Google tools only when the user has authorized (token file exists)."""
    if not auth.configured():
        return
    from . import calendar, drive, gmail, tasks, youtube
    for m in (gmail, youtube, calendar, drive, tasks):
        m.register()
