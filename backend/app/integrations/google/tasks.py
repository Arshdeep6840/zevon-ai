from ...core.tools import registry
from . import auth


def list_tasks():
    r = auth.service("tasks", "v1").tasks().list(tasklist="@default", showCompleted=False, maxResults=50).execute()
    return "\n".join(f"[{t['id']}] {t['title']}" + (f" (due {t['due'][:10]})" if t.get("due") else "")
                     for t in r.get("items", [])) or "No open tasks."


def create_task(title: str, notes: str = ""):
    t = auth.service("tasks", "v1").tasks().insert(tasklist="@default", body={"title": title, "notes": notes}).execute()
    return f"Task created (id {t['id']})."


def register():
    registry.tool("tasks_list", "List open Google Tasks.", auth.opt(), risk="read")(list_tasks)
    registry.tool("tasks_create", "Create a Google Task.", {"type": "object", "properties": {
        "title": {"type": "string"}, "notes": {"type": "string"}}, "required": ["title"]}, risk="safe_write")(create_task)
