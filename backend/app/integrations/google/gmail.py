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


SYSTEM_LABELS = {"inbox": "INBOX", "unread": "UNREAD", "starred": "STARRED", "important": "IMPORTANT",
                 "spam": "SPAM", "trash": "TRASH", "sent": "SENT", "draft": "DRAFT"}


def _label_ids(svc, names: str) -> list[str]:
    """Comma-separated label names (or ids) -> label ids. System labels and existing user labels only."""
    wanted = [n.strip() for n in names.split(",") if n.strip()]
    if not wanted:
        return []
    by_name = {l["name"].lower(): l["id"] for l in svc.users().labels().list(userId="me").execute().get("labels", [])}
    out = []
    for w in wanted:
        lid = SYSTEM_LABELS.get(w.lower()) or by_name.get(w.lower()) or (w if w.isupper() else None)
        if not lid:
            raise ValueError(f"Unknown label '{w}'. Use gmail_list_labels or gmail_create_label.")
        out.append(lid)
    return out


def list_labels():
    ls = _service().users().labels().list(userId="me").execute().get("labels", [])
    return "\n".join(f"{l['name']} ({l['id']})" for l in ls)


def modify_labels(message_id: str, add: str = "", remove: str = ""):
    svc = _service()
    body = {"addLabelIds": _label_ids(svc, add), "removeLabelIds": _label_ids(svc, remove)}
    svc.users().messages().modify(userId="me", id=message_id, body=body).execute()
    return f"Updated labels on {message_id}: +{add or '-'} -{remove or '-'}"


def archive_email(message_id: str):
    return modify_labels(message_id, remove="INBOX")


def mark_read(message_id: str):
    return modify_labels(message_id, remove="UNREAD")


def create_label(name: str):
    l = _service().users().labels().create(userId="me", body={"name": name}).execute()
    return f"Label created: {l['name']} ({l['id']})"


def trash_email(message_id: str):
    _service().users().messages().trash(userId="me", id=message_id).execute()
    return f"Moved {message_id} to trash."


def register():
    registry.tool("gmail_search_emails", "Search Gmail (Gmail query syntax, e.g. 'is:unread newer_than:1d').",
                  {"type": "object", "properties": {"query": {"type": "string"}, "max_results": {"type": "integer"}}},
                  risk="read")(search_emails)
    registry.tool("gmail_read_email", "Read one email by id.", auth.obj(message_id="string"), risk="read")(read_email)
    registry.tool("gmail_create_draft", "Create an email draft (does not send).",
                  auth.obj(to="string", subject="string", body="string"), risk="safe_write")(create_draft)
    registry.tool("gmail_send_email", "Send an email. Requires user approval.",
                  auth.obj(to="string", subject="string", body="string"), risk="sensitive")(send_email)
    registry.tool("gmail_list_labels", "List Gmail labels.", auth.opt(), risk="read")(list_labels)
    registry.tool("gmail_modify_labels", "Add/remove labels on an email (comma-separated names).", {
        "type": "object", "properties": {"message_id": {"type": "string"}, "add": {"type": "string"},
                                         "remove": {"type": "string"}}, "required": ["message_id"]}, risk="safe_write")(modify_labels)
    registry.tool("gmail_archive_email", "Archive an email (remove from inbox).", auth.obj(message_id="string"),
                  risk="safe_write")(archive_email)
    registry.tool("gmail_mark_read", "Mark an email as read.", auth.obj(message_id="string"), risk="safe_write")(mark_read)
    registry.tool("gmail_create_label", "Create a Gmail label.", auth.obj(name="string"), risk="safe_write")(create_label)
    registry.tool("gmail_trash_email", "Move an email to trash. Requires user approval.", auth.obj(message_id="string"),
                  risk="sensitive")(trash_email)
