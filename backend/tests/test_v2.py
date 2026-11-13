import importlib.util
import json
import sys
import textwrap
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import ROOT, Settings, settings
from app.core import voice
from app.core.llm import LLMProvider, LLMResponse, ToolCall
from app.core.memory import Store
from app.core.memory_tools import register_memory_tools
from app.core.notify import Notifier
from app.core.tools import ToolRegistry, registry
from app.integrations.tools import browser, terminal
from app.main import create_app

has = lambda m: importlib.util.find_spec(m) is not None  # noqa: E731


class FakeLLM(LLMProvider):
    def __init__(self, script):
        self.script = list(script)

    def chat(self, messages, tools=None):
        return self.script.pop(0)


def client(tmp_path, script=()):
    cfg = Settings(db_path=":memory:", allowed_folders=[str(tmp_path)], vector_memory="off",
                   vapid_key_file=str(tmp_path / "vapid.pem"))
    return TestClient(create_app(cfg, FakeLLM(script), start_scheduler=False, load_extensions=False))


# ---------- terminal ----------
def test_terminal_allowlist(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "allowed_folders", [str(tmp_path)])
    (tmp_path / "x.txt").write_text("hi")
    assert "x.txt" in terminal.run_command("ls")
    for bad in ["rm -rf x.txt", "ls | cat", "ls; whoami", "echo hi > f", "git push", "git diff --output=/tmp/o",
                "ls /etc", "python -c 'print(1)'", "ls $(whoami)"]:
        with pytest.raises(PermissionError):
            terminal.run_command(bad)


# ---------- browser SSRF ----------
@pytest.mark.parametrize("url", ["http://127.0.0.1/", "http://localhost:8000/", "http://169.254.169.254/latest",
                                 "file:///etc/passwd", "http://[::1]/", "ftp://x.com"])
def test_browser_blocks_internal(url):
    with pytest.raises(PermissionError):
        browser.check_url(url)


def test_browser_domain_allowlist(monkeypatch):
    monkeypatch.setattr(settings, "browser_allowed_domains", ["example.com"])
    with pytest.raises(PermissionError):
        browser.check_url("https://evil.org/")


def test_html_to_text():
    assert browser.html_to_text("<script>x()</script><p>Hello <b>world</b></p>") == "Hello world"


# ---------- notifications / push ----------
def test_notifier_stores_and_api(tmp_path):
    c = client(tmp_path)
    c.app.state.notifier.notify("Brief", "3 unread")
    n = c.get("/api/notifications").json()
    assert n[0]["title"] == "Brief"
    c.post("/api/notifications/read")
    assert c.get("/api/notifications?unread=true").json() == []
    assert c.post("/api/push/subscribe", json={"endpoint": "https://e/1", "keys": {"p256dh": "a", "auth": "b"}}).json()["ok"]
    assert len(c.app.state.store.push_subs()) == 1


@pytest.mark.skipif(not has("pywebpush"), reason="pywebpush not installed")
def test_vapid_key_generation(tmp_path):
    c = client(tmp_path)
    key = c.get("/api/push/public-key").json()["key"]
    assert len(key) == 87 and (tmp_path / "vapid.pem").exists()   # 65-byte uncompressed P-256 point, base64url


# ---------- conditional rules ----------
class FakeEngine:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []
        self.policy = type("P", (), {"kill_switch": False})()

    def run(self, session, text):
        self.calls.append(text)
        return {"reply": self.replies.pop(0)}


def test_email_trigger_flow(monkeypatch):
    from app.integrations.google import auth, gmail
    from app.triggers.email_trigger import EmailTrigger
    store = Store(":memory:")
    notifier = Notifier(store, Settings(vapid_key_file="/tmp/x.pem"))
    store.add_instruction("Important mail", "conditional", "If the email is from my boss, summarize it", "email:new")
    monkeypatch.setattr(auth, "configured", lambda: True)
    ids = {"v": ["m1", "m2"]}
    monkeypatch.setattr(gmail, "list_message_ids", lambda q, n: ids["v"])
    eng = FakeEngine(["IGNORE", "Boss wants the report today."])
    t = EmailTrigger(eng, store, notifier)
    t.poll()
    assert eng.calls == []                                   # first poll = baseline, nothing fires
    ids["v"] = ["m3", "m2", "m1"]
    t.poll()
    assert len(eng.calls) == 1 and "m3" in eng.calls[0] and "gmail_read_email" in eng.calls[0]
    t.poll()
    assert len(eng.calls) == 1                               # already seen
    ids["v"] = ["m4", "m3"]
    t.poll()
    titles = [n["title"] for n in store.notifications()]
    assert titles == ["Important mail"]                      # IGNORE reply produced no notification


def test_conditional_validation(tmp_path):
    c = client(tmp_path)
    bad = c.post("/api/instructions", json={"name": "x", "kind": "conditional", "text": "t", "schedule": "whatever"})
    assert bad.status_code == 422
    ok = c.post("/api/instructions", json={"name": "x", "kind": "conditional", "text": "t", "schedule": "email:new"})
    assert ok.status_code == 200


def test_scheduler_notifies():
    from app.scheduler.runner import ZevonScheduler
    store = Store(":memory:")
    notifier = Notifier(store, Settings(vapid_key_file="/tmp/x.pem"))
    s = ZevonScheduler(FakeEngine(["Your day: 2 meetings"]), store, notifier)
    s._run({"id": 1, "name": "Morning briefing", "text": "brief me"})
    assert store.notifications()[0]["body"] == "Your day: 2 meetings"


# ---------- voice ----------
def test_voice_endpoints_501_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(voice, "stt_available", lambda: False)
    monkeypatch.setattr(voice, "tts_available", lambda cfg: False)
    c = client(tmp_path)
    assert c.post("/api/voice/transcribe", content=b"abc").status_code == 501
    assert c.post("/api/voice/speak", json={"text": "hi"}).status_code == 501
    assert c.get("/api/capabilities").json()["voice_stt"] is False


def test_voice_transcribe_wiring(tmp_path, monkeypatch):
    monkeypatch.setattr(voice, "stt_available", lambda: True)
    monkeypatch.setattr(voice, "transcribe", lambda audio, cfg: f"heard {len(audio)} bytes")
    assert client(tmp_path).post("/api/voice/transcribe", content=b"12345").json()["text"] == "heard 5 bytes"


# ---------- vector memory ----------
def fake_embed(texts):
    vocab = ["python", "email", "coffee", "fastapi", "dog", "music"]
    return [[float(w in t.lower()) + 0.01 for w in vocab] for t in texts]


@pytest.mark.skipif(not has("chromadb"), reason="chromadb not installed")
def test_vector_memory_semantic_recall(tmp_path):
    from app.core.vector_memory import VectorMemory
    vm = VectorMemory(str(tmp_path / "chroma"), fake_embed)
    reg, store = ToolRegistry(), Store(":memory:")
    register_memory_tools(reg, store, vm)
    reg.get("memory_remember").func("I love coffee in the morning")
    reg.get("memory_remember").func("My dog is called Rex")
    reg.get("memory_remember").func("I build APIs with FastAPI")
    assert "dog" in reg.get("memory_recall").func("tell me about my dog")
    assert "FastAPI" in reg.get("memory_recall").func("fastapi stuff")


def test_recall_falls_back_when_vector_fails():
    class Broken:
        def add(self, *a): raise RuntimeError("no embed model")
        def search(self, *a): raise RuntimeError("no embed model")
    reg, store = ToolRegistry(), Store(":memory:")
    register_memory_tools(reg, store, Broken())
    reg.get("memory_remember").func("likes green tea")
    assert "green tea" in reg.get("memory_recall").func("tea")


# ---------- extensions + MCP ----------
def test_plugin_loader_loads_example(monkeypatch):
    from app.integrations.plugin_loader import load_plugins
    monkeypatch.setattr(settings, "plugins_dir", str(ROOT / "plugins"))
    assert "example_hello" in load_plugins(registry)
    assert registry.get("hello_time").func().startswith("20")


def test_plugin_loader_survives_broken_plugin(tmp_path, monkeypatch):
    from app.integrations.plugin_loader import load_plugins
    (tmp_path / "bad.py").write_text("raise RuntimeError('boom')")
    monkeypatch.setattr(settings, "plugins_dir", str(tmp_path))
    store = Store(":memory:")
    assert load_plugins(ToolRegistry(), store) == []
    assert store.audit_log()[0]["outcome"] == "load failed"


@pytest.mark.skipif(not has("mcp"), reason="mcp not installed")
def test_mcp_server_tools_registered_and_gated(tmp_path, monkeypatch):
    from app.integrations.mcp_client import register_mcp
    srv = tmp_path / "srv.py"
    srv.write_text(textwrap.dedent("""
        try:
            from mcp.server.mcpserver import MCPServer as Srv      # mcp 2.x
        except ImportError:
            from mcp.server.fastmcp import FastMCP as Srv          # mcp 1.x
        m = Srv("demo")
        @m.tool()
        def add(a: int, b: int) -> int:
            "Add two numbers"
            return a + b
        @m.tool()
        def wipe() -> str:
            "Dangerous"
            return "wiped"
        m.run()
    """))
    cfg = tmp_path / "mcp.json"
    cfg.write_text(json.dumps({"servers": {"demo": {"command": sys.executable, "args": [str(srv)], "read_tools": ["add"]}}}))
    monkeypatch.setattr(settings, "mcp_config", str(cfg))
    reg = ToolRegistry()
    names = register_mcp(reg, Store(":memory:"))
    assert sorted(names) == ["mcp_demo_add", "mcp_demo_wipe"]
    assert reg.get("mcp_demo_add").risk == "read" and reg.get("mcp_demo_wipe").risk == "sensitive"
    assert reg.get("mcp_demo_add").func(a=2, b=3) == "5"


# ---------- google + third-party connectors ----------
def test_google_tools_only_with_token(tmp_path, monkeypatch):
    from app.integrations import google
    monkeypatch.setattr(settings, "google_token_file", str(tmp_path / "nope.json"))
    before = {t.name for t in registry.all()}
    google.register_all()
    assert {t.name for t in registry.all()} == before
    tok = tmp_path / "tok.json"
    tok.write_text("{}")
    monkeypatch.setattr(settings, "google_token_file", str(tok))
    google.register_all()
    names = {t.name: t.risk for t in registry.all()}
    for n in ["gmail_search_emails", "youtube_search_videos", "calendar_list_events", "drive_search_files", "tasks_create"]:
        assert n in names
    assert names["calendar_create_event"] == "sensitive" and names["gmail_send_email"] == "sensitive"


def _resp(data):
    return httpx.Response(200, json=data, request=httpx.Request("GET", "http://x"))


def test_todoist_handles_v1_shape(monkeypatch):
    from app.integrations.productivity import todoist
    monkeypatch.setattr(httpx, "get", lambda url, **k: _resp({"results": [{"id": "9", "content": "Buy milk", "due": {"date": "2026-11-13"}}]}))
    assert "Buy milk" in todoist.list_tasks() and "2026-11-13" in todoist.list_tasks()
    assert todoist.API.endswith("/api/v1")


def test_notion_title_and_slack_gate(monkeypatch):
    from app.integrations.productivity import notion, slack
    monkeypatch.setattr(httpx, "post", lambda url, **k: _resp({"results": [
        {"id": "p1", "object": "page", "properties": {"Name": {"type": "title", "title": [{"plain_text": "Roadmap"}]}}}]}))
    assert "Roadmap" in notion.search("road")
    slack.register()
    assert registry.get("slack_post_message").risk == "sensitive"


def test_new_tools_visible_in_api(tmp_path):
    c = client(tmp_path)
    names = {t["name"] for t in c.get("/api/tools").json()}
    assert {"terminal_run", "browser_read_page", "memory_recall", "fs_list_dir"} <= names
