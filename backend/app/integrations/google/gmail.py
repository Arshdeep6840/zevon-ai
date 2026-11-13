"""Gmail connector (official API + OAuth 2.0). Send is approval-gated; drafts are automatic."""
import base64
from email.mime.text import MIMEText

from ...core.tools import registry
from . import auth


def _service():
    return auth.service("gmail", "v1")


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


def list_message_ids(query: str = "is:unread", max_results: int = 10) -> list[str]:
    res = _service().users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    return [m["id"] for m in res.get("messages", [])]


def search_emails(query: str = "is:unread", max_results: int = 10):
    svc, out = _service(), []
    for mid in list_message_ids(query, max_results):
        full = svc.users().messages().get(userId="me", id=mid, format="metadata",
                                          metadataHeaders=["From", "Subject", "Date"]).execute()
        out.append(f"[{mid}] {_header(full, 'from')} | {_header(full, 'subject')} | {_header(full, 'date')}")
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


def register():
    registry.tool("gmail_search_emails", "Search Gmail (Gmail query syntax, e.g. 'is:unread newer_than:1d').",
                  {"type": "object", "properties": {"query": {"type": "string"}, "max_results": {"type": "integer"}}},
                  risk="read")(search_emails)
    registry.tool("gmail_read_email", "Read one email by id.", auth.obj(message_id="string"), risk="read")(read_email)
    registry.tool("gmail_create_draft", "Create an email draft (does not send).",
                  auth.obj(to="string", subject="string", body="string"), risk="safe_write")(create_draft)
    registry.tool("gmail_send_email", "Send an email. Requires user approval.",
                  auth.obj(to="string", subject="string", body="string"), risk="sensitive")(send_email)
