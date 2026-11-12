"""Gmail connector (official API + OAuth 2.0). Run scripts/google_auth.py once to authorize.
Tools are registered only if a token exists. Send is approval-gated; drafts are automatic."""
import base64
from email.mime.text import MIMEText
from pathlib import Path

from ...config import settings
from ...core.tools import registry

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.compose",
          "https://www.googleapis.com/auth/gmail.send"]


def _service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    return build("gmail", "v1", credentials=Credentials.from_authorized_user_file(settings.google_token_file, SCOPES))


def _header(msg, name):
    return next((h["value"] for h in msg["payload"]["headers"] if h["name"].lower() == name), "")


def _body(payload) -> str:
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode(errors="replace")
    for part in payload.get("parts", []):
        text = _body(part) if part.get("mimeType", "").startswith(("text/plain", "multipart")) else ""
        if text:
            return text
    return ""


def search_emails(query: str = "is:unread", max_results: int = 10):
    svc = _service()
    ids = svc.users().messages().list(userId="me", q=query, maxResults=max_results).execute().get("messages", [])
    out = []
    for m in ids:
        full = svc.users().messages().get(userId="me", id=m["id"], format="metadata",
                                          metadataHeaders=["From", "Subject", "Date"]).execute()
        out.append(f"[{m['id']}] {_header(full, 'from')} | {_header(full, 'subject')} | {_header(full, 'date')}")
    return "\n".join(out) or "No emails found."


def read_email(message_id: str):
    full = _service().users().messages().get(userId="me", id=message_id, format="full").execute()
    return f"From: {_header(full, 'from')}\nSubject: {_header(full, 'subject')}\n\n{_body(full['payload'])[:3500]}"


def _raw(to, subject, body):
    m = MIMEText(body)
    m["to"], m["subject"] = to, subject
    return {"raw": base64.urlsafe_b64encode(m.as_bytes()).decode()}


def create_draft(to: str, subject: str, body: str):
    d = _service().users().drafts().create(userId="me", body={"message": _raw(to, subject, body)}).execute()
    return f"Draft created (id {d['id']})."


def send_email(to: str, subject: str, body: str):
    _service().users().messages().send(userId="me", body=_raw(to, subject, body)).execute()
    return f"Email sent to {to}."


def _obj(**props):
    return {"type": "object", "properties": {k: {"type": "string"} for k in props}, "required": list(props)}


def register():
    if not Path(settings.google_token_file).exists():
        return
    registry.tool("gmail_search_emails", "Search Gmail (Gmail query syntax, e.g. 'is:unread newer_than:1d').",
                  {"type": "object", "properties": {"query": {"type": "string"}, "max_results": {"type": "integer"}}},
                  risk="read")(search_emails)
    registry.tool("gmail_read_email", "Read one email by id.", _obj(message_id=1), risk="read")(read_email)
    registry.tool("gmail_create_draft", "Create an email draft (does not send).", _obj(to=1, subject=1, body=1),
                  risk="safe_write")(create_draft)
    registry.tool("gmail_send_email", "Send an email. Requires user approval.", _obj(to=1, subject=1, body=1),
                  risk="sensitive")(send_email)
