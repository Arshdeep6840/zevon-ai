"""Conditional-rule triggers. A conditional instruction's `schedule` field holds the trigger string."""
import re

TRIGGER_HELP = {
    "email:new": "When a new email arrives in the inbox",
    "calendar:soon:15": "When a calendar event starts within N minutes (default 15)",
    "file:new:<folder>": "When a new file appears in an authorized folder",
    "slack:new:<channel_id>": "When a new message is posted in a Slack channel",
    "time:every:30m@09:00-18:00": "Every N minutes/hours, optionally only inside a daily time window",
}
PATTERNS = [r"^email:new$", r"^calendar:soon(:\d{1,3})?$", r"^file:new:.+$", r"^slack:new:[A-Za-z0-9]+$",
            r"^time:every:\d{1,3}[mh](@\d{2}:\d{2}-\d{2}:\d{2})?$"]


def valid_trigger(s: str) -> bool:
    return any(re.match(p, s or "") for p in PATTERNS)
