import httpx

from app.config import Settings
from app.core.llm import OllamaProvider
from app.core.memory import Store
from app.core.agent_engine import AgentEngine
from app.core.permissions import PermissionPolicy
from app.core.tools import ToolRegistry
from app.scheduler.runner import JarvisScheduler


def _resp(message):
    return httpx.Response(200, json={"message": message}, request=httpx.Request("POST", "http://x"))


def test_ollama_provider_parses_tool_calls_and_strips_think(monkeypatch):
    replies = [{"content": "<think>hmm</think>", "tool_calls": [{"function": {"name": "memory_recall", "arguments": {"query": "x"}}}]},
               {"content": "<think>done</think>Hello!"}]
    seen = {}

    def fake_post(url, json=None, timeout=None):
        seen["url"], seen["payload"] = url, json
        return _resp(replies.pop(0))
    monkeypatch.setattr(httpx, "post", fake_post)
    llm = OllamaProvider("http://localhost:11434", "qwen3:8b")
    r1 = llm.chat([{"role": "user", "content": "hi"}], [{"type": "function"}])
    assert r1.tool_calls[0].name == "memory_recall" and r1.tool_calls[0].arguments == {"query": "x"}
    assert seen["url"].endswith("/api/chat") and "tools" in seen["payload"]
    assert llm.chat([]).content == "Hello!"


def test_ollama_down_gives_friendly_error(monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectError("refused")
    monkeypatch.setattr(httpx, "post", boom)
    assert "Could not reach Ollama" in OllamaProvider("http://localhost:1", "m").chat([]).content


def test_scheduler_registers_cron_jobs_and_runs():
    store = Store(":memory:")
    ran = []

    class Eng:
        def run(self, session, text):
            ran.append((session, text))
    store.add_instruction("brief", "scheduled", "Summarize emails", "0 8 * * *")
    store.add_instruction("bad", "scheduled", "x", "not a cron")
    s = JarvisScheduler(Eng(), store)
    s.reload()
    assert len(s.sched.get_jobs()) == 1
    s._run(store.instructions(kind="scheduled")[0])
    assert ran and ran[0][1] == "Summarize emails"


def test_permanent_instructions_and_memory_reach_system_prompt():
    store = Store(":memory:")
    store.add_instruction("rule", "permanent", "Never send email without approval")
    store.remember("User prefers short answers")
    eng = AgentEngine(None, ToolRegistry(), store, PermissionPolicy())
    prompt = eng._system()
    assert "Never send email" in prompt and "short answers" in prompt
