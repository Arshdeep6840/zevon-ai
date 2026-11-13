import httpx

from ...config import settings
from ...core.tools import registry

API = "https://api.notion.com/v1"


def _h():
    return {"Authorization": f"Bearer {settings.notion_token}", "Notion-Version": "2022-06-28"}


def _title(page):
    for p in page.get("properties", {}).values():
        if p.get("type") == "title":
            return "".join(t["plain_text"] for t in p["title"]) or "(untitled)"
    return "(untitled)"


def search(query: str):
    r = httpx.post(f"{API}/search", headers=_h(), json={"query": query, "page_size": 10}, timeout=20)
    r.raise_for_status()
    return "\n".join(f"[{x['id']}] {_title(x)} ({x['object']})" for x in r.json()["results"]) or "No results."


def create_page(title: str, content: str = ""):
    if not settings.notion_parent_page:
        return "Set ZEVON_NOTION_PARENT_PAGE (a page id shared with your integration)."
    body = {"parent": {"page_id": settings.notion_parent_page},
            "properties": {"title": {"title": [{"text": {"content": title}}]}},
            "children": [{"object": "block", "type": "paragraph",
                          "paragraph": {"rich_text": [{"text": {"content": content[:1900]}}]}}] if content else []}
    r = httpx.post(f"{API}/pages", headers=_h(), json=body, timeout=20)
    r.raise_for_status()
    return f"Created Notion page: {r.json().get('url')}"


def register():
    registry.tool("notion_search", "Search Notion pages.", {"type": "object", "properties": {"query": {"type": "string"}},
                                                          "required": ["query"]}, risk="read")(search)
    registry.tool("notion_create_page", "Create a Notion page under the configured parent page.", {
        "type": "object", "properties": {"title": {"type": "string"}, "content": {"type": "string"}},
        "required": ["title"]}, risk="safe_write")(create_page)
