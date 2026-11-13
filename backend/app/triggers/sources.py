"""Trigger sources. Event details are NEVER pasted into the prompt (they may be attacker-controlled); the agent
reads them through tools, so they stay marked as untrusted."""
import time
from datetime import datetime
from pathlib import Path

from ..config import settings
from ..integrations.google import auth as google_auth
from ..integrations.system.filesystem import safe_path
from .base import RuleTrigger


class CalendarTrigger(RuleTrigger):
    name, prefix = "calendar", "calendar:soon"

    def available(self):
        return google_auth.configured()

    def events(self, rule):
        from ..integrations.google import calendar
        parts = rule["schedule"].split(":")
        lead = int(parts[2]) if len(parts) > 2 else 15
        return [(f"{eid}@{start}", f"A calendar event (id {eid}) starts within {lead} minutes. Use calendar_list_events to read it.")
                for eid, start in calendar.upcoming_keys(lead)]


class FileTrigger(RuleTrigger):
    name, prefix = "file", "file:new:"

    def events(self, rule):
        folder = safe_path(rule["schedule"][len(self.prefix):])
        ctx = (f"A new file appeared in the folder {folder}. Use fs_list_dir and, if relevant, fs_read_file to look at it.")
        return [(f"{p.name}:{int(p.stat().st_mtime)}", ctx) for p in sorted(Path(folder).iterdir())
                if p.is_file() and not p.name.startswith(".")]


class SlackTrigger(RuleTrigger):
    name, prefix = "slack", "slack:new:"

    def available(self):
        return bool(settings.slack_token)

    def events(self, rule):
        from ..integrations.productivity import slack
        ch = rule["schedule"][len(self.prefix):]
        msgs = slack._call("conversations.history", channel=ch, limit=10)["messages"]
        return [(m["ts"], f"A new message was posted in Slack channel {ch}. Use slack_read_channel to read it.") for m in msgs]


class TimeTrigger(RuleTrigger):
    """time:every:30m@09:00-18:00  -> fires once per interval, only inside the optional daily window."""
    name, prefix, baseline = "time", "time:every:", False

    @staticmethod
    def parse(schedule: str):
        spec, _, window = schedule[len("time:every:"):].partition("@")
        seconds = int(spec[:-1]) * (60 if spec[-1] == "m" else 3600)
        return seconds, window

    def events(self, rule):
        seconds, window = self.parse(rule["schedule"])
        now = datetime.now(self._tz())
        if window:
            start, end = window.split("-")
            if not (start <= now.strftime("%H:%M") < end):
                return []
        return [(str(int(time.time() // seconds)), "A time-based rule is due now.")]

    @staticmethod
    def _tz():
        try:
            from zoneinfo import ZoneInfo
            return ZoneInfo(settings.timezone)
        except Exception:
            return None
