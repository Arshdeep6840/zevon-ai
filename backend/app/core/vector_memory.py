"""Semantic memory with ChromaDB. Embeddings come from Ollama (local), so nothing leaves your machine."""
import httpx


class OllamaEmbedder:
    def __init__(self, host, model):
        self.host, self.model = host.rstrip("/"), model

    def __call__(self, texts: list[str]) -> list[list[float]]:
        r = httpx.post(f"{self.host}/api/embed", json={"model": self.model, "input": texts}, timeout=60)
        r.raise_for_status()
        return r.json()["embeddings"]


class VectorMemory:
    def __init__(self, path: str, embed):
        import chromadb
        self.embed = embed
        self.col = chromadb.PersistentClient(path=path).get_or_create_collection(
            "zevon_memories", metadata={"hnsw:space": "cosine"})

    @classmethod
    def create(cls, cfg, embed=None):
        if cfg.vector_memory.lower() in ("off", "0", "false"):
            return None
        try:
            import chromadb  # noqa: F401
        except ImportError:
            return None
        return cls(cfg.chroma_dir, embed or OllamaEmbedder(cfg.ollama_host, cfg.embed_model))

    def add(self, mem_id, text: str):
        self.col.upsert(ids=[str(mem_id)], documents=[text], embeddings=self.embed([text]))

    def delete(self, mem_id):
        self.col.delete(ids=[str(mem_id)])

    def search(self, query: str, n: int = 5) -> list[str]:
        count = self.col.count()
        if not count:
            return []
        res = self.col.query(query_embeddings=self.embed([query]), n_results=min(n, count))
        return res["documents"][0]
