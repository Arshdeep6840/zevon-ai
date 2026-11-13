from .tools import ToolRegistry


def register_memory_tools(registry: ToolRegistry, store, vector=None):
    def remember(text: str):
        mid = store.remember(text)
        if vector:
            try:
                vector.add(mid, text)
            except Exception as e:  # e.g. embedding model not pulled; plain-text search still works
                store.audit("memory", "vector_add", str(e)[:200], "failed")
        return f"Saved memory #{mid}"

    def recall(query: str = ""):
        if vector and query:
            try:
                hits = vector.search(query)
                if hits:
                    return "\n".join(f"- {h}" for h in hits)
            except Exception as e:
                store.audit("memory", "vector_search", str(e)[:200], "failed")
        return "\n".join(f"- {m['text']}" for m in store.memories(query)) or "No matching memories."

    registry.tool("memory_remember", "Save a fact or preference about the user for future conversations.",
                  {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
                  risk="safe_write")(remember)
    registry.tool("memory_recall", "Search saved long-term memories (semantic when available).",
                  {"type": "object", "properties": {"query": {"type": "string"}}}, risk="read")(recall)
