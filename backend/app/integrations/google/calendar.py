from datetime import datetime, timedelta, timezone

from ...config import settings
from ...core.tools import registry
from . import auth


def list_events(days: int = 7):
    now = datetime.now(timezone.utc)
    r = auth.service("calendar", "v3").events().list(
        calendarId="primary", timeMin=now.isoformat(), timeMax=(now + timedelta(days=days)).isoformat(),
        singleEvents=True, orderBy="startTime", maxResults=25).execute()
    out = []
    for e in r.get("items", []):
        start = e["start"].get("dateTime", e["start"].get("date"))
        out.append(f"[{e['id']}] {start} — {e.get('summary', '(no title)')}")
    return "\n".join(out) or "No upcoming events."


def upcoming_keys(minutes: int = 15):
    """(event id, start) for events starting within the next N minutes (used by the calendar trigger)."""
    now = datetime.now(timezone.utc)
    r = auth.service("calendar", "v3").events().list(
        calendarId="primary", timeMin=now.isoformat(), timeMax=(now + timedelta(minutes=minutes)).isoformat(),
        singleEvents=True, orderBy="startTime", maxResults=10).execute()
    return [(e["id"], e["start"].get("dateTime", e["start"].get("date"))) for e in r.get("items", [])]


def create_event(summary: str, start: str, end: str, description: str = ""):
    """start/end are ISO 8601, e.g. 2026-11-20T15:00:00 (interpreted in ZEVON_TIMEZONE)."""
    tz = settings.timezone
    body = {"summary": summary, "description": description,
            "start": {"dateTime": start, "timeZone": tz}, "end": {"dateTime": end, "timeZone": tz}}
    e = auth.service("calendar", "v3").events().insert(calendarId="primary", body=body).execute()
    return f"Event created: {e.get('htmlLink', e['id'])}"


def register():
    registry.tool("calendar_list_events", "List upcoming Google Calendar events.", auth.opt(days="integer"),
                  risk="read")(list_events)
    registry.tool("calendar_create_event", "Create a calendar event. Requires user approval.", {
        "type": "object", "properties": {"summary": {"type": "string"}, "start": {"type": "string"},
                                         "end": {"type": "string"}, "description": {"type": "string"}},
        "required": ["summary", "start", "end"]}, risk="sensitive")(create_event)
