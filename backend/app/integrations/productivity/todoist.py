import httpx

from ...config import settings
from ...core.tools import registry

API = "https://api.todoist.com/api/v1"   # REST v2 was retired (HTTP 410)


def _h():
    return {"Authorization": f"Bearer {settings.todoist_token}"}


def list_tasks(project_id: str = ""):
    r = httpx.get(f"{API}/tasks", headers=_h(), params={"project_id": project_id} if project_id else {}, timeout=20)
    r.raise_for_status()
    data = r.json()
    items = data.get("results", []) if isinstance(data, dict) else data
    return "\n".join(f"[{t['id']}] {t['content']}" + (f" (due {t['due']['date']})" if t.get("due") else "")
                     for t in items) or "No tasks."


def create_task(content: str, due_string: str = "", priority: int = 1):
    body = {"content": content, "priority": priority}
    if due_string:
        body["due_string"] = due_string
    r = httpx.post(f"{API}/tasks", headers=_h(), json=body, timeout=20)
    r.raise_for_status()
    return f"Todoist task created (id {r.json()['id']})."


def register():
    registry.tool("todoist_list_tasks", "List open Todoist tasks.", {"type": "object", "properties": {
        "project_id": {"type": "string"}}}, risk="read")(list_tasks)
    registry.tool("todoist_create_task", "Create a Todoist task (due_string like 'tomorrow 9am').", {
        "type": "object", "properties": {"content": {"type": "string"}, "due_string": {"type": "string"},
                                         "priority": {"type": "integer"}}, "required": ["content"]},
        risk="safe_write")(create_task)
