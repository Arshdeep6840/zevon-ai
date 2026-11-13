"""LLM providers behind one interface: Ollama (local), OpenAI-compatible (llama.cpp, vLLM, LM Studio, OpenAI,
OpenRouter, Groq, Gemini-compat...), Anthropic. All support tool calling; Ollama + OpenAI-compatible also stream."""
import ipaddress
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx


@dataclass
class ToolCall:
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMProvider(ABC):
    name = "llm"
    local = True   # False = prompts leave this machine

    @abstractmethod
    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> LLMResponse: ...

    def chat_stream(self, messages, tools=None):
        """Yield ("token", text) pieces, then ("final", LLMResponse). Default: one chunk (non-streaming providers)."""
        resp = self.chat(messages, tools)
        if resp.content:
            yield ("token", resp.content)
        yield ("final", resp)


class ThinkFilter:
    """Strips <think>...</think> from a token stream, even when tags are split across chunks."""
    OPEN, CLOSE = "<think>", "</think>"

    def __init__(self):
        self.buf, self.inside = "", False

    def feed(self, s: str) -> str:
        self.buf += s
        out = ""
        while True:
            if self.inside:
                i = self.buf.find(self.CLOSE)
                if i < 0:
                    self.buf = self.buf[-7:]
                    return out
                self.buf, self.inside = self.buf[i + len(self.CLOSE):], False
                continue
            i = self.buf.find(self.OPEN)
            if i >= 0:
                out += self.buf[:i]
                self.buf, self.inside = self.buf[i + len(self.OPEN):], True
                continue
            keep = next((k for k in range(min(len(self.buf), 6), 0, -1) if self.OPEN.startswith(self.buf[-k:])), 0)
            out += self.buf[:len(self.buf) - keep]
            self.buf = self.buf[len(self.buf) - keep:]
            return out

    def flush(self) -> str:
        out = "" if self.inside else self.buf
        self.buf = ""
        return out


def _strip_think(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()


def _args(a) -> dict:
    if isinstance(a, str):
        try:
            return json.loads(a) if a.strip() else {}
        except json.JSONDecodeError:
            return {}
    return a or {}


def _is_local_url(url: str) -> bool:
    host = urlparse(url).hostname or ""
    if host in ("localhost", "host.docker.internal") or host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback
    except ValueError:
        return False


# ---------------- Ollama ----------------
class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, host: str, model: str, timeout: float = 180.0):
        self.host, self.model, self.timeout = host.rstrip("/"), model, timeout

    def _err(self, e):
        return (f"[LLM error] Could not reach Ollama at {self.host} "
                f"(is it running, and did you `ollama pull {self.model}`?): {e}")

    @staticmethod
    def _call(tc) -> ToolCall:
        fn = tc.get("function", {})
        return ToolCall(name=fn.get("name", ""), arguments=_args(fn.get("arguments", {})))

    def chat(self, messages, tools=None) -> LLMResponse:
        payload = {"model": self.model, "messages": messages, "stream": False}
        if tools:
            payload["tools"] = tools
        try:
            r = httpx.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout)
            r.raise_for_status()
        except httpx.HTTPError as e:
            return LLMResponse(content=self._err(e))
        msg = r.json().get("message", {})
        return LLMResponse(content=_strip_think(msg.get("content")),
                           tool_calls=[self._call(tc) for tc in msg.get("tool_calls") or []])

    def chat_stream(self, messages, tools=None):
        payload = {"model": self.model, "messages": messages, "stream": True}
        if tools:
            payload["tools"] = tools
        content, calls, flt = "", [], ThinkFilter()
        try:
            with httpx.stream("POST", f"{self.host}/api/chat", json=payload, timeout=self.timeout) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line:
                        continue
                    msg = json.loads(line).get("message", {})
                    shown = flt.feed(msg.get("content") or "")
                    if shown:
                        content += shown
                        yield ("token", shown)
                    calls += [self._call(tc) for tc in msg.get("tool_calls") or []]
        except httpx.HTTPError as e:
            text = self._err(e)
            yield ("token", text)
            yield ("final", LLMResponse(content=text))
            return
        tail = flt.flush()
        if tail:
            content += tail
            yield ("token", tail)
        yield ("final", LLMResponse(content=content.strip(), tool_calls=calls))


# ---------------- OpenAI-compatible (llama.cpp, vLLM, LM Studio, OpenAI, OpenRouter, ...) ----------------
class OpenAICompatProvider(LLMProvider):
    name = "openai"

    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 180.0):
        self.base, self.key, self.model, self.timeout = base_url.rstrip("/"), api_key, model, timeout
        self.local = _is_local_url(base_url)

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.key:
            h["Authorization"] = f"Bearer {self.key}"
        return h

    @staticmethod
    def convert(messages: list[dict]) -> list[dict]:
        """Zevon messages -> OpenAI format (adds tool_call ids, JSON-string arguments)."""
        out, pending, n = [], [], 0
        for m in messages:
            if m["role"] == "assistant" and m.get("tool_calls"):
                calls, pending = [], []
                for tc in m["tool_calls"]:
                    n += 1
                    pending.append(f"call_{n}")
                    calls.append({"id": f"call_{n}", "type": "function", "function": {
                        "name": tc["function"]["name"], "arguments": json.dumps(tc["function"]["arguments"])}})
                out.append({"role": "assistant", "content": m.get("content") or None, "tool_calls": calls})
            elif m["role"] == "tool":
                out.append({"role": "tool", "tool_call_id": pending.pop(0) if pending else "call_0", "content": m["content"]})
            else:
                out.append({"role": m["role"], "content": m["content"]})
        return out

    def _payload(self, messages, tools, stream):
        p = {"model": self.model, "messages": self.convert(messages), "stream": stream}
        if tools:
            p["tools"] = tools
        return p

    def _err(self, e):
        return f"[LLM error] Could not get a reply from {self.base}: {e}"

    def chat(self, messages, tools=None) -> LLMResponse:
        try:
            r = httpx.post(f"{self.base}/chat/completions", headers=self._headers(),
                           json=self._payload(messages, tools, False), timeout=self.timeout)
            r.raise_for_status()
            msg = r.json()["choices"][0]["message"]
        except (httpx.HTTPError, KeyError, IndexError) as e:
            return LLMResponse(content=self._err(e))
        calls = [ToolCall(tc["function"]["name"], _args(tc["function"].get("arguments"))) for tc in msg.get("tool_calls") or []]
        return LLMResponse(content=_strip_think(msg.get("content")), tool_calls=calls)

    def chat_stream(self, messages, tools=None):
        content, acc, flt = "", {}, ThinkFilter()
        try:
            with httpx.stream("POST", f"{self.base}/chat/completions", headers=self._headers(),
                              json=self._payload(messages, tools, True), timeout=self.timeout) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    choices = json.loads(data).get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    shown = flt.feed(delta.get("content") or "")
                    if shown:
                        content += shown
                        yield ("token", shown)
                    for tc in delta.get("tool_calls") or []:
                        slot = acc.setdefault(tc.get("index", 0), {"name": "", "args": ""})
                        fn = tc.get("function", {})
                        slot["name"] += fn.get("name") or ""
                        slot["args"] += fn.get("arguments") or ""
        except httpx.HTTPError as e:
            text = self._err(e)
            yield ("token", text)
            yield ("final", LLMResponse(content=text))
            return
        tail = flt.flush()
        if tail:
            content += tail
            yield ("token", tail)
        calls = [ToolCall(v["name"], _args(v["args"])) for _, v in sorted(acc.items()) if v["name"]]
        yield ("final", LLMResponse(content=content.strip(), tool_calls=calls))


# ---------------- Anthropic ----------------
class AnthropicProvider(LLMProvider):
    name = "anthropic"
    local = False

    def __init__(self, api_key: str, model: str, timeout: float = 180.0, max_tokens: int = 2048):
        self.key, self.model, self.timeout, self.max_tokens = api_key, model, timeout, max_tokens

    @staticmethod
    def convert(messages: list[dict]):
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        out, pending, n = [], [], 0
        for m in messages:
            if m["role"] == "system":
                continue
            if m["role"] == "assistant" and m.get("tool_calls"):
                blocks, pending = [], []
                if m.get("content"):
                    blocks.append({"type": "text", "text": m["content"]})
                for tc in m["tool_calls"]:
                    n += 1
                    pending.append(f"toolu_{n}")
                    blocks.append({"type": "tool_use", "id": f"toolu_{n}", "name": tc["function"]["name"],
                                   "input": tc["function"]["arguments"]})
                out.append({"role": "assistant", "content": blocks})
            elif m["role"] == "tool":
                block = {"type": "tool_result", "tool_use_id": pending.pop(0) if pending else "toolu_0", "content": m["content"]}
                if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list):
                    out[-1]["content"].append(block)      # consecutive tool results share one user turn
                else:
                    out.append({"role": "user", "content": [block]})
            else:
                out.append({"role": m["role"], "content": m["content"]})
        return system, out

    def chat(self, messages, tools=None) -> LLMResponse:
        system, msgs = self.convert(messages)
        payload = {"model": self.model, "max_tokens": self.max_tokens, "system": system, "messages": msgs}
        if tools:
            payload["tools"] = [{"name": t["function"]["name"], "description": t["function"]["description"],
                                 "input_schema": t["function"]["parameters"]} for t in tools]
        try:
            r = httpx.post("https://api.anthropic.com/v1/messages", timeout=self.timeout, json=payload,
                           headers={"x-api-key": self.key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
            r.raise_for_status()
            blocks = r.json()["content"]
        except (httpx.HTTPError, KeyError) as e:
            return LLMResponse(content=f"[LLM error] Anthropic request failed: {e}")
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        calls = [ToolCall(b["name"], b.get("input", {})) for b in blocks if b.get("type") == "tool_use"]
        return LLMResponse(content=text.strip(), tool_calls=calls)


def make_provider(settings) -> LLMProvider:
    p = settings.llm_provider.lower()
    if p == "ollama":
        return OllamaProvider(settings.ollama_host, settings.model)
    if p in ("openai", "llamacpp", "llama.cpp", "vllm", "lmstudio", "openrouter"):
        return OpenAICompatProvider(settings.openai_base_url, settings.openai_api_key, settings.model)
    if p == "anthropic":
        return AnthropicProvider(settings.anthropic_api_key, settings.model)
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
