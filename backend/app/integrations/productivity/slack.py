import httpx

from ...config import settings
from ...core.tools import registry

API = "https://slack.com/api"


def _call(method, **params):
    r = httpx.post(f"{API}/{method}", headers={"Authorization": f"Bearer {settings.slack_token}"}, data=params, timeout=20)
    r.raise_for_status()
    d = r.json()
    if not d.get("ok"):
        raise RuntimeError(f"Slack error: {d.get('error')}")
    return d


def list_channels():
    d = _call("conversations.list", types="public_channel", limit=100, exclude_archived="true")
    return "\n".join(f"[{c['id']}] #{c['name']}" for c in d["channels"]) or "No channels."


def read_channel(channel_id: str, limit: int = 10):
    d = _call("conversations.history", channel=channel_id, limit=limit)
    return "\n".join(f"{m.get('user', 'bot')}: {m.get('text', '')}" for m in d["messages"]) or "No messages."


def post_message(channel_id: str, text: str):
    _call("chat.postMessage", channel=channel_id, text=text)
    return f"Posted to {channel_id}."


def register():
    registry.tool("slack_list_channels", "List public Slack channels.", {"type": "object", "properties": {}},
                  risk="read")(list_channels)
    registry.tool("slack_read_channel", "Read recent messages from a Slack channel id.", {
        "type": "object", "properties": {"channel_id": {"type": "string"}, "limit": {"type": "integer"}},
        "required": ["channel_id"]}, risk="read")(read_channel)
    registry.tool("slack_post_message", "Post a Slack message. Requires user approval.", {
        "type": "object", "properties": {"channel_id": {"type": "string"}, "text": {"type": "string"}},
        "required": ["channel_id", "text"]}, risk="sensitive")(post_message)
