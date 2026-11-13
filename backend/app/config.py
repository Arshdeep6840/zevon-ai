"""Central configuration, read from environment variables (see .env.example)."""
import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv():
    """Load KEY=VALUE lines from the project-root .env (real environment variables win)."""
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


def E(name, default="", cast=str):
    return field(default_factory=lambda: cast(os.getenv(name, default)))


def L(name, default="", sep=","):
    return field(default_factory=lambda: [p.strip() for p in os.getenv(name, default).split(sep) if p.strip()])


@dataclass
class Settings:
    # core
    llm_provider: str = E("ZEVON_LLM_PROVIDER", "ollama")
    ollama_host: str = E("OLLAMA_HOST", "http://localhost:11434")
    model: str = E("ZEVON_MODEL", "qwen3:8b")
    db_path: str = E("ZEVON_DB", str(ROOT / "data" / "zevon.db"))
    api_token: str = E("ZEVON_API_TOKEN")
    allowed_folders: list = L("ZEVON_ALLOWED_FOLDERS", sep=os.pathsep)
    max_agent_steps: int = E("ZEVON_MAX_STEPS", "6", int)
    timezone: str = E("ZEVON_TIMEZONE", "UTC")
    cors_origins: list = L("ZEVON_CORS_ORIGINS", "capacitor://localhost,http://localhost,https://localhost,"
                           "tauri://localhost,http://tauri.localhost,http://localhost:5173")
    # google
    google_token_file: str = E("ZEVON_GOOGLE_TOKEN", str(ROOT / "data" / "google_token.json"))
    email_poll_minutes: int = E("ZEVON_EMAIL_POLL_MIN", "5", int)
    # memory
    vector_memory: str = E("ZEVON_VECTOR_MEMORY", "auto")        # auto | off
    embed_model: str = E("ZEVON_EMBED_MODEL", "nomic-embed-text")  # `ollama pull nomic-embed-text`
    chroma_dir: str = E("ZEVON_CHROMA_DIR", str(ROOT / "data" / "chroma"))
    # voice
    whisper_model: str = E("ZEVON_WHISPER_MODEL", "base")
    piper_model: str = E("ZEVON_PIPER_MODEL")                    # path to a Piper .onnx voice
    # third party
    notion_token: str = E("ZEVON_NOTION_TOKEN")
    notion_parent_page: str = E("ZEVON_NOTION_PARENT_PAGE")
    todoist_token: str = E("ZEVON_TODOIST_TOKEN")
    slack_token: str = E("ZEVON_SLACK_TOKEN")
    # browser / terminal
    browser_allowed_domains: list = L("ZEVON_BROWSER_DOMAINS")   # empty = any public site
    terminal_extra: list = L("ZEVON_TERMINAL_EXTRA")             # extra allowlisted program names
    # extensions / mcp / push
    plugins_dir: str = E("ZEVON_PLUGINS_DIR", str(ROOT / "plugins"))
    mcp_config: str = E("ZEVON_MCP_CONFIG", str(ROOT / "data" / "mcp_servers.json"))
    vapid_key_file: str = E("ZEVON_VAPID_KEY", str(ROOT / "data" / "vapid_private.pem"))
    vapid_subject: str = E("ZEVON_VAPID_SUBJECT", "mailto:admin@example.com")


settings = Settings()
