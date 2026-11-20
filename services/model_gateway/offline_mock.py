"""Offline embedded provider for testing and zero-dependency local assistant mode."""

import asyncio
from typing import AsyncIterator, List, Optional, Dict, Any
from datetime import datetime
from packages.shared_schemas.models import Message, ModelCard, Role
from .base import BaseModelProvider


class OfflineMockProvider(BaseModelProvider):
    """Fallback provider when no external LLM engine (Ollama/llama.cpp) is running."""

    def __init__(self):
        self.models = [
            ModelCard(
                id="zevon-offline-compact",
                name="Zevon Offline Compact",
                provider="offline-embedded",
                parameter_size="1B-simulated",
                quantization="Q4_K_M",
                context_length=4096,
                is_active=True,
                is_installed=True,
                description="Zero-dependency local response engine for offline operation and testing.",
            ),
            ModelCard(
                id="zevon-reasoning-mock",
                name="Zevon Reasoning (Local)",
                provider="offline-embedded",
                parameter_size="7B-simulated",
                quantization="Q4_K_S",
                context_length=8192,
                is_active=False,
                is_installed=True,
                description="Multi-step task reasoning model simulation.",
            ),
        ]

    async def check_health(self) -> bool:
        return True

    async def list_models(self) -> List[ModelCard]:
        return self.models

    async def stream_chat(
        self,
        messages: List[Message],
        model_name: str,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        last_msg = messages[-1].content if messages else "Hello"
        prompt_lower = last_msg.lower().strip()

        # Simulated response generator
        response = self._generate_response(prompt_lower, last_msg)

        # Stream words with slight delay to simulate natural streaming
        words = response.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            await asyncio.sleep(0.02)

    def _generate_response(self, prompt: str, original: str) -> str:
        if any(w in prompt for w in ["who are you", "what are you", "your name"]):
            return (
                "I am **Zevon**, your local-first, open-source personal AI assistant. "
                "I run entirely on your local infrastructure with no mandatory paid APIs or cloud dependencies."
            )
        elif any(w in prompt for w in ["time", "date", "clock"]):
            now = datetime.now()
            return f"The current local time is **{now.strftime('%I:%M %p')}** on **{now.strftime('%A, %B %d, %Y')}**."
        elif "calculate" in prompt or any(op in prompt for op in ["+", "-", "*", "/", "sqrt"]):
            return (
                "I've evaluated the mathematical expression through the MCP Calculator tool. "
                "For advanced calculations, Zevon uses verified local tools with strict parameter safety."
            )
        elif "mcp" in prompt or "protocol" in prompt:
            return (
                "Zevon utilizes the **Model Context Protocol (MCP)** as its universal tool and context standard. "
                "Both built-in tools (files, calculator, notes) and third-party tools expose standard MCP interfaces, "
                "ensuring any model and tool can be connected without rewriting core orchestrator code."
            )
        elif "agent" in prompt:
            return (
                "Zevon supports a hierarchical **Agent Calling API**. When a request involves multi-step work, "
                "the orchestrator coordinates specialized sub-agents with checkpoints and explicit approvals for high-impact actions."
            )
        else:
            return (
                f"Hello! I received your message: *\"{original}\"*\n\n"
                f"I am operating in **local offline mode**. You can chat with me, manage conversations, "
                f"or connect local Ollama models (`qwen2.5`, `deepseek-r1`, `llama3.2`) for full neural generation."
            )
