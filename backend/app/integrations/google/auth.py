"""Shared Google OAuth helper. Run scripts/google_auth.py once; all Google connectors reuse the token."""
from pathlib import Path

from ...config import settings

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/tasks",
]


def configured() -> bool:
    return Path(settings.google_token_file).exists()


def service(name: str, version: str):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials.from_authorized_user_file(settings.google_token_file, SCOPES)
    return build(name, version, credentials=creds, cache_discovery=False)


def obj(**props):
    """Tiny JSON-schema helper: obj(a="string", b="integer") -> required string/integer params."""
    return {"type": "object", "properties": {k: {"type": v} for k, v in props.items()}, "required": list(props)}


def opt(**props):
    return {"type": "object", "properties": {k: {"type": v} for k, v in props.items()}}
