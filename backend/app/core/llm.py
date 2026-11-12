"""LLM provider interface. Ollama today; llama.cpp / vLLM / cloud later by subclassing LLMProvider."""
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

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
    @abstractmethod
    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> LLMResponse: ...


class OllamaProvider(LLMProvider):
    def __init__(self, host: str, model: str, timeout: float = 180.0):
        self.host, self.model, self.timeout = host.rstrip("/"), model, timeout

    def chat(self, messages, tools=None) -> LLMResponse:
        payload = {"model": self.model, "messages": messages, "stream": False}
        if tools:
            payload["tools"] = tools
        try:
            r = httpx.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout)
            r.raise_for_status()
        except httpx.HTTPError as e:
            return LLMResponse(content=f"[LLM error] Could not reach Ollama at {self.host} "
                                       f"(is it running, and did you `ollama pull {self.model}`?): {e}")
        msg = r.json().get("message", {})
        content = re.sub(r"<think>.*?</think>", "", msg.get("content", "") or "", flags=re.S).strip()
        calls = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function", {})
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            calls.append(ToolCall(name=fn.get("name", ""), arguments=args))
        return LLMResponse(content=content, tool_calls=calls)


def make_provider(settings) -> LLMProvider:
    if settings.llm_provider == "ollama":
        return OllamaProvider(settings.ollama_host, settings.model)
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
