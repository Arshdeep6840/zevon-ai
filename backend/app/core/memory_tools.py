from .tools import ToolRegistry


def register_memory_tools(registry: ToolRegistry, store):
    registry.tool("memory_remember", "Save a fact or preference about the user for future conversations.",
                  {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
                  risk="safe_write")(lambda text: f"Saved memory #{store.remember(text)}")

    def recall(query: str = ""):
        return "\n".join(f"- {m['text']}" for m in store.memories(query)) or "No matching memories."
    registry.tool("memory_recall", "Search saved long-term memories.",
                  {"type": "object", "properties": {"query": {"type": "string"}}}, risk="read")(recall)
