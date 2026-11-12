"""Central configuration, read from environment variables (see .env.example)."""
import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv():
    """Load KEY=VALUE lines from the project-root .env (real environment variables win)."""
    f = Path(__file__).resolve().parents[2] / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


def _folders() -> list[str]:
    raw = os.getenv("JARVIS_ALLOWED_FOLDERS", "")
    return [p for p in raw.split(os.pathsep) if p]


@dataclass
class Settings:
    llm_provider: str = field(default_factory=lambda: os.getenv("JARVIS_LLM_PROVIDER", "ollama"))
    ollama_host: str = field(default_factory=lambda: os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    model: str = field(default_factory=lambda: os.getenv("JARVIS_MODEL", "qwen3:8b"))
    db_path: str = field(default_factory=lambda: os.getenv("JARVIS_DB", str(Path(__file__).resolve().parents[2] / "data" / "jarvis.db")))
    api_token: str = field(default_factory=lambda: os.getenv("JARVIS_API_TOKEN", ""))
    allowed_folders: list[str] = field(default_factory=_folders)
    max_agent_steps: int = field(default_factory=lambda: int(os.getenv("JARVIS_MAX_STEPS", "6")))
    google_token_file: str = field(default_factory=lambda: os.getenv("JARVIS_GOOGLE_TOKEN", str(Path(__file__).resolve().parents[2] / "data" / "google_token.json")))
    frontend_dir: str = str(Path(__file__).resolve().parents[2] / "frontend")


settings = Settings()
