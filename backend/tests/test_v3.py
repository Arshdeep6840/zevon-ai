import json
import sys
import types
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings, settings
from app.core.agent_engine import AgentEngine
from app.core.llm import (AnthropicProvider, LLMProvider, LLMResponse, OllamaProvider, OpenAICompatProvider,
                          ThinkFilter, ToolCall)
from app.core.memory import Store
from app.core.permissions import PermissionPolicy
from app.core.tools import ToolRegistry
from app.main import create_app


class FakeLLM(LLMProvider):
    def __init__(self, script):
        self.script, self.seen = list(script), []

    def chat(self, messages, tools=None):
        self.seen.append(messages)
        return self.script.pop(0) if self.script else LLMResponse(content="ok")


def client(tmp_path, script=(), db=":memory:", **kw):
    cfg = Settings(db_path=db, allowed_folders=[str(tmp_path)], vector_memory="off", planning="off",
                   vapid_key_file=str(tmp_path / "v.pem"), **kw)
    from app.integrations.system import filesystem
    filesystem.settings.allowed_folders = [str(tmp_path)]
    return TestClient(create_app(cfg, FakeLLM(script), start_scheduler=False, load_extensions=False))


def sse(text):
    return [json.loads(b[6:]) for b in text.split("\n\n") if b.startswith("data: ")]


# ---------- streaming ----------
def test_think_filter_split_tags():
    f = ThinkFilter()
    out = "".join(f.feed(c) for c in ["Hel", "<thi", "nk>secret</th", "ink>lo ", "<b>x"]) + f.flush()
    assert out == "Hello <b>x"


class FakeStream:
    def __init__(self, lines): self.lines = lines
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def raise_for_status(self): pass
    def iter_lines(self): return iter(self.lines)


def test_ollama_streaming_tokens_and_tool_calls(monkeypatch):
    lines = [json.dumps({"message": {"content": c}}) for c in ["<thi", "nk>hmm</think>Hel", "lo"]]
    lines.append(json.dumps({"message": {"tool_calls": [{"function": {"name": "fs_list_dir", "arguments": {"path": "/x"}}}]}}))
    monkeypatch.setattr(httpx, "stream", lambda *a, **k: FakeStream(lines))
    ev = list(OllamaProvider("http://h", "m").chat_stream([{"role": "user", "content": "hi"}], []))
    assert "".join(v for k, v in ev if k == "token") == "Hello"
    final = ev[-1][1]
    assert final.content == "Hello" and final.tool_calls[0].arguments == {"path": "/x"}


def test_openai_compat_convert_chat_and_stream(monkeypatch):
    msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"},
            {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "a", "arguments": {"x": 1}}},
                                                                {"function": {"name": "b", "arguments": {}}}]},
            {"role": "tool", "tool_name": "a", "content": "ra"}, {"role": "tool", "tool_name": "b", "content": "rb"}]
    out = OpenAICompatProvider.convert(msgs)
    assert out[2]["tool_calls"][0]["function"]["arguments"] == '{"x": 1}'
    assert [m["tool_call_id"] for m in out[3:]] == ["call_1", "call_2"]
    p = OpenAICompatProvider("http://localhost:8080/v1", "", "m")
    assert p.local is True and OpenAICompatProvider("https://api.openai.com/v1", "k", "m").local is False
    resp = httpx.Response(200, request=httpx.Request("POST", "http://x"), json={"choices": [{"message": {
        "content": "hi", "tool_calls": [{"function": {"name": "fs_list_dir", "arguments": "{\"path\": \"/a\"}"}}]}}]})
    monkeypatch.setattr(httpx, "post", lambda *a, **k: resp)
    r = p.chat([{"role": "user", "content": "x"}], [])
    assert r.content == "hi" and r.tool_calls[0].arguments == {"path": "/a"}
    sl = ['data: {"choices":[{"delta":{"content":"He"}}]}', 'data: {"choices":[{"delta":{"content":"llo"}}]}',
          'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"name":"fs_list_dir","arguments":"{\\"pa"}}]}}]}',
          'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"th\\": \\"/q\\"}"}}]}}]}', "data: [DONE]"]
    monkeypatch.setattr(httpx, "stream", lambda *a, **k: FakeStream(sl))
    ev = list(p.chat_stream([{"role": "user", "content": "x"}], []))
    assert ev[-1][1].content == "Hello" and ev[-1][1].tool_calls[0] == ToolCall("fs_list_dir", {"path": "/q"})


def test_anthropic_convert_and_parse(monkeypatch):
    msgs = [{"role": "system", "content": "sys"}, {"role": "user", "content": "u"},
            {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "a", "arguments": {"x": 1}}},
                                                                {"function": {"name": "b", "arguments": {}}}]},
            {"role": "tool", "tool_name": "a", "content": "ra"}, {"role": "tool", "tool_name": "b", "content": "rb"}]
    system, out = AnthropicProvider.convert(msgs)
    assert system == "sys" and out[1]["content"][0]["type"] == "tool_use"
    assert len(out) == 3 and [b["tool_use_id"] for b in out[2]["content"]] == ["toolu_1", "toolu_2"]   # merged tool results
    resp = httpx.Response(200, request=httpx.Request("POST", "http://x"),
                          json={"content": [{"type": "text", "text": "ok"}, {"type": "tool_use", "name": "a", "input": {"q": 1}}]})
    monkeypatch.setattr(httpx, "post", lambda *a, **k: resp)
    r = AnthropicProvider("k", "m").chat(msgs, [{"type": "function", "function": {"name": "a", "description": "d", "parameters": {}}}])
    assert r.content == "ok" and r.tool_calls == [ToolCall("a", {"q": 1})]
    assert AnthropicProvider("k", "m").local is False


def test_chat_stream_endpoint(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    c = client(tmp_path, [LLMResponse(tool_calls=[ToolCall("fs_list_dir", {"path": str(tmp_path)})]), LLMResponse(content="Found a.txt")])
    r = c.post("/api/chat/stream", json={"message": "list", "session": "s1"})
    assert r.headers["content-type"].startswith("text/event-stream")
    ev = sse(r.text)
    kinds = [e["type"] for e in ev]
    assert kinds[0] == "tool" and ev[0]["status"] == "running" and ev[1]["status"] == "ok"
    assert "token" in kinds and ev[-1]["type"] == "done" and ev[-1]["reply"] == "Found a.txt"


# ---------- sessions, summaries, planning, loop guard ----------
def test_sessions_list_and_delete(tmp_path):
    c = client(tmp_path, [LLMResponse(content="a"), LLMResponse(content="b")])
    c.post("/api/chat", json={"message": "first chat about cats", "session": "s1"})
    c.post("/api/chat", json={"message": "second", "session": "scheduled-3"})
    s = {x["session"]: x for x in c.get("/api/sessions").json()}
    assert s["s1"]["title"].startswith("first chat") and s["s1"]["kind"] == "chat" and s["scheduled-3"]["kind"] == "automation"
    c.delete("/api/sessions/s1")
    assert "s1" not in {x["session"] for x in c.get("/api/sessions").json()}


def test_long_history_is_summarized():
    store, llm = Store(":memory:"), FakeLLM([])
    for i in range(10):
        store.add_message("s", "user" if i % 2 == 0 else "assistant", f"m{i}")
    eng = AgentEngine(llm, ToolRegistry(), store, PermissionPolicy(), history_keep=3, summarize_after=5, planning="off")
    llm.script = [LLMResponse(content="SUMMARY: user talked about m0-m6"), LLMResponse(content="answer")]
    eng.run("s", "new question")
    assert store.get_summary("s")[0].startswith("SUMMARY")
    final_call = llm.seen[1]
    assert "SUMMARY: user talked" in final_call[0]["content"]                       # summary injected into system prompt
    assert [m["content"] for m in final_call[1:]] == ["m7", "m8", "m9", "new question"]   # only recent kept verbatim


def test_planning_emits_plan_and_injects_it():
    llm = FakeLLM([LLMResponse(content="1. Search email\n2. Summarize\n3. Create task"), LLMResponse(content="done")])
    eng = AgentEngine(llm, ToolRegistry(), Store(":memory:"), PermissionPolicy(), planning="auto")
    ev = list(eng.run_stream("s", "Check my email, then summarize it and also create a task"))
    assert ev[0]["type"] == "plan" and len(ev[0]["steps"]) == 3
    assert "1. Search email" in llm.seen[1][0]["content"]
    llm2 = FakeLLM([LLMResponse(content="hello")])
    AgentEngine(llm2, ToolRegistry(), Store(":memory:"), PermissionPolicy(), planning="auto").run("s", "hi")
    assert len(llm2.seen) == 1       # simple message: no planning call


def test_repeated_identical_calls_are_blocked():
    reg = ToolRegistry()
    n = {"c": 0}
    reg.tool("ping", "p", risk="read")(lambda: n.__setitem__("c", n["c"] + 1) or "pong")
    llm = FakeLLM([LLMResponse(tool_calls=[ToolCall("ping", {})]) for _ in range(6)])
    res = AgentEngine(llm, reg, Store(":memory:"), PermissionPolicy(), max_steps=6, planning="off").run("s", "go")
    assert n["c"] == 3 and [s["status"] for s in res["steps"]].count("loop_blocked") == 3


# ---------- per-tool policies, memories, rule toggles ----------
def test_tool_policy_overrides_persist(tmp_path):
    db = str(tmp_path / "z.db")
    target = tmp_path / "f.txt"
    target.write_text("x")
    script = lambda: [LLMResponse(tool_calls=[ToolCall("fs_delete_file", {"path": str(target)})]), LLMResponse(content="ok")]  # noqa: E731
    c = client(tmp_path, script(), db=db)
    row = next(p for p in c.get("/api/policies").json() if p["name"] == "fs_delete_file")
    assert row["default"] == "approve" and row["override"] is None
    assert c.put("/api/policies/fs_delete_file", json={"decision": "allow"}).status_code == 200
    r = c.post("/api/chat", json={"message": "delete"}).json()
    assert r["steps"][0]["status"] == "ok" and not target.exists()            # allowed without approval
    c2 = client(tmp_path, script(), db=db)                                      # fresh app, same database
    assert next(p for p in c2.get("/api/policies").json() if p["name"] == "fs_delete_file")["effective"] == "allow"
    c2.put("/api/policies/fs_delete_file", json={"decision": "deny"})
    assert c2.post("/api/chat", json={"message": "delete"}).json()["steps"][0]["status"] == "denied"
    c2.put("/api/policies/fs_delete_file", json={"decision": "default"})
    assert c2.put("/api/policies/nope", json={"decision": "allow"}).status_code == 404
    assert c2.put("/api/policies/fs_delete_file", json={"decision": "bogus"}).status_code == 422


def test_memories_crud_updates_vector(tmp_path):
    class Vec:
        def __init__(self): self.ops = []
        def add(self, i, t): self.ops.append(("add", i, t))
        def delete(self, i): self.ops.append(("del", i))
    cfg = Settings(db_path=":memory:", vector_memory="off", vapid_key_file=str(tmp_path / "v.pem"))
    vec = Vec()
    c = TestClient(create_app(cfg, FakeLLM([]), start_scheduler=False, load_extensions=False, vector=vec))
    mid = c.post("/api/memories", json={"text": "likes tea"}).json()["id"]
    c.put(f"/api/memories/{mid}", json={"text": "likes green tea"})
    assert c.get("/api/memories").json()[0]["text"] == "likes green tea"
    assert c.get("/api/memories?q=green").json()[0]["id"] == mid
    c.delete(f"/api/memories/{mid}")
    assert c.get("/api/memories").json() == [] and vec.ops == [("add", mid, "likes tea"), ("add", mid, "likes green tea"), ("del", mid)]
    assert c.put("/api/memories/999", json={"text": "x"}).status_code == 404


def test_rule_toggle_endpoint(tmp_path):
    c = client(tmp_path)
    iid = c.post("/api/instructions", json={"name": "r", "kind": "permanent", "text": "be brief"}).json()["id"]
    c.patch(f"/api/instructions/{iid}", json={"enabled": False})
    assert c.get("/api/instructions").json()[0]["enabled"] == 0
    assert "be brief" not in c.app.state.engine._system()
    c.patch(f"/api/instructions/{iid}", json={"enabled": True})
    assert "be brief" in c.app.state.engine._system()
    assert len(c.get("/api/triggers").json()) == 5


# ---------- triggers ----------
def test_valid_triggers():
    from app.triggers import valid_trigger
    for ok in ["email:new", "calendar:soon", "calendar:soon:30", "file:new:/home/me/Downloads", "slack:new:C123ABC",
               "time:every:30m", "time:every:2h@09:00-18:00"]:
        assert valid_trigger(ok), ok
    for bad in ["", "whatever", "email:old", "time:every:30", "slack:new:#general", "calendar:soon:x"]:
        assert not valid_trigger(bad), bad


class FakeEngine:
    def __init__(self):
        self.calls, self.policy = [], type("P", (), {"kill_switch": False})()

    def run(self, session, text):
        self.calls.append(text)
        return {"reply": "IGNORE" if "ignoreme" in text else "Heads up!"}


def test_file_trigger_baseline_then_fires(tmp_path, monkeypatch):
    from app.triggers.sources import FileTrigger
    monkeypatch.setattr(settings, "allowed_folders", [str(tmp_path)])
    (tmp_path / "old.txt").write_text("1")
    store, eng = Store(":memory:"), FakeEngine()
    store.add_instruction("Watch", "conditional", "tell me", f"file:new:{tmp_path}")
    t = FileTrigger(eng, store, type("N", (), {"notify": lambda s, a, b: store.add_notification(a, b)})())
    t.poll()
    assert eng.calls == []                                   # baseline
    (tmp_path / "new.pdf").write_text("2")
    t.poll(); t.poll()
    assert len(eng.calls) == 1 and "new.pdf" not in eng.calls[0]       # filename never put in the prompt
    assert store.notifications()[0]["title"] == "Watch"


def test_file_trigger_rejects_unauthorized_folder(tmp_path, monkeypatch):
    from app.triggers.sources import FileTrigger
    monkeypatch.setattr(settings, "allowed_folders", [str(tmp_path)])
    store = Store(":memory:")
    store.add_instruction("Bad", "conditional", "x", "file:new:/etc")
    FileTrigger(FakeEngine(), store, None).poll()
    assert store.audit_log()[0]["outcome"] == "poll failed"


def test_calendar_and_slack_triggers(monkeypatch):
    from app.integrations.google import auth, calendar
    from app.integrations.productivity import slack
    from app.triggers.sources import CalendarTrigger, SlackTrigger
    store, eng = Store(":memory:"), FakeEngine()
    notifier = type("N", (), {"notify": lambda s, a, b: store.add_notification(a, b)})()
    store.add_instruction("Cal", "conditional", "prep me", "calendar:soon:30")
    store.add_instruction("Sl", "conditional", "alert me", "slack:new:C1")
    monkeypatch.setattr(auth, "configured", lambda: True)
    monkeypatch.setattr(settings, "slack_token", "xoxb")
    evs = {"cal": [("e1", "t1")], "sl": [{"ts": "1.0"}]}
    monkeypatch.setattr(calendar, "upcoming_keys", lambda m: evs["cal"])
    monkeypatch.setattr(slack, "_call", lambda method, **k: {"messages": evs["sl"]})
    cal, sl = CalendarTrigger(eng, store, notifier), SlackTrigger(eng, store, notifier)
    cal.poll(); sl.poll()
    assert eng.calls == []
    evs["cal"].append(("e2", "t2")); evs["sl"].append({"ts": "2.0"})
    cal.poll(); sl.poll()
    assert len(eng.calls) == 2 and "within 30 minutes" in eng.calls[0] and "slack_read_channel" in eng.calls[1]


def test_time_trigger_interval_and_window():
    from app.triggers.sources import TimeTrigger
    assert TimeTrigger.parse("time:every:30m@09:00-18:00") == (1800, "09:00-18:00")
    assert TimeTrigger.parse("time:every:2h") == (7200, "")
    store, eng = Store(":memory:"), FakeEngine()
    notifier = type("N", (), {"notify": lambda s, a, b: store.add_notification(a, b)})()
    store.add_instruction("Always", "conditional", "drink water", "time:every:30m")
    store.add_instruction("Never", "conditional", "x ignoreme", "time:every:30m@12:00-12:00")   # empty window
    t = TimeTrigger(eng, store, notifier)
    t.poll(); t.poll()
    assert len(eng.calls) == 1 and "drink water" in eng.calls[0]      # once per interval bucket, empty window never fires


# ---------- connectors ----------
def test_gmail_labels_archive_and_trash(monkeypatch):
    from app.integrations.google import gmail
    svc = MagicMock()
    svc.users.return_value.labels.return_value.list.return_value.execute.return_value = {"labels": [{"name": "Receipts", "id": "Label_7"}]}
    monkeypatch.setattr(gmail, "_service", lambda: svc)
    gmail.modify_labels("m1", add="receipts", remove="unread")
    svc.users.return_value.messages.return_value.modify.assert_called_with(
        userId="me", id="m1", body={"addLabelIds": ["Label_7"], "removeLabelIds": ["UNREAD"]})
    gmail.archive_email("m2")
    assert svc.users.return_value.messages.return_value.modify.call_args.kwargs["body"]["removeLabelIds"] == ["INBOX"]
    with pytest.raises(ValueError):
        gmail.modify_labels("m3", add="NoSuchLabel")
    from app.core.tools import registry
    gmail.register()
    assert registry.get("gmail_trash_email").risk == "sensitive" and registry.get("gmail_archive_email").risk == "safe_write"


def test_drive_create_doc_and_todoist_complete(monkeypatch):
    from app.integrations.google import auth, drive
    from app.integrations.productivity import todoist
    mods = {"googleapiclient": types.ModuleType("googleapiclient"), "googleapiclient.http": types.ModuleType("googleapiclient.http")}
    mods["googleapiclient.http"].MediaIoBaseUpload = lambda fh, mimetype: ("media", mimetype)
    for k, v in mods.items():
        monkeypatch.setitem(sys.modules, k, v)
    svc = MagicMock()
    svc.files.return_value.create.return_value.execute.return_value = {"id": "d1", "webViewLink": "https://docs/d1"}
    monkeypatch.setattr(auth, "service", lambda *a: svc)
    assert "https://docs/d1" in drive.create_doc("Notes", "hello")
    assert svc.files.return_value.create.call_args.kwargs["body"]["mimeType"] == "application/vnd.google-apps.document"
    seen = {}
    monkeypatch.setattr(httpx, "post", lambda url, **k: seen.update(url=url) or httpx.Response(204, request=httpx.Request("POST", url)))
    assert "Completed" in todoist.complete_task("42") and seen["url"].endswith("/api/v1/tasks/42/close")


def test_browser_action_whitelist():
    from app.integrations.tools import browser
    ok = browser.validate_actions('[{"do":"fill","selector":"#q","value":"hi"},{"do":"press","key":"Enter"},{"do":"wait","ms":99999}]')
    assert ok[2]["ms"] == 5000
    for bad in [[], [{"do": "eval", "code": "x"}], [{"do": "click"}], "notjson[", [{"do": "click", "selector": "a"}] * 11]:
        with pytest.raises((ValueError, json.JSONDecodeError)):
            browser.validate_actions(bad)
    with pytest.raises(PermissionError):
        browser.interact("http://127.0.0.1/admin", [{"do": "click", "selector": "a"}])
    with pytest.raises(PermissionError):
        browser.screenshot("http://169.254.169.254/")


def test_terminal_ask_mode(tmp_path, monkeypatch):
    from app.integrations.tools import terminal
    from app.core.tools import registry
    monkeypatch.setattr(settings, "allowed_folders", [str(tmp_path)])
    terminal.register_ask_mode()
    assert registry.get("terminal_run_any").risk == "sensitive"
    assert terminal.run_any("echo hello").strip() == "hello"
    for bad in ["sudo ls", "echo a | cat", "rm x; ls", "dd if=/dev/zero of=x"]:
        with pytest.raises(PermissionError):
            terminal.run_any(bad)


def test_fcm_send_and_notifier(monkeypatch):
    from app.core import fcm
    from app.core.notify import Notifier
    monkeypatch.setattr(fcm, "_access_token", lambda path: ("tok", "proj"))
    sent = []

    def post(url, headers=None, json=None, timeout=None):
        sent.append((url, json["message"]["token"]))
        code = 404 if json["message"]["token"] == "dead" else 200
        return httpx.Response(code, text="UNREGISTERED" if code == 404 else "{}", request=httpx.Request("POST", url))
    monkeypatch.setattr(httpx, "post", post)
    assert fcm.send_fcm("sa.json", ["good", "dead"], "T", "B") == ["dead"]
    assert sent[0][0].endswith("/projects/proj/messages:send")
    store = Store(":memory:")
    store.add_fcm_token("good"); store.add_fcm_token("dead")
    n = Notifier(store, Settings(fcm_service_account="sa.json", vapid_key_file="/tmp/x.pem"))
    n.notify("Hi", "there")
    assert store.fcm_tokens() == ["good"] and store.notifications()[0]["title"] == "Hi"


def test_capabilities_report_provider(tmp_path):
    caps = client(tmp_path).get("/api/capabilities").json()
    assert caps["provider"] == "llm" and caps["local_model"] is True and caps["planning"] == "off" and caps["terminal_ask"] is False
