"""Configuration settings for Zevon API server."""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Zevon Personal AI Assistant"
    version: str = "0.1.0"
    host: str = "127.0.0.1"
    port: int = 8000
    db_path: str = os.getenv("ZEVON_DB_PATH", "zevon.db")
    ollama_url: str = os.getenv("ZEVON_OLLAMA_URL", "http://localhost:11434")
    default_profile: str = "personal"
    default_model: str = "zevon-offline-compact"
    force_offline: bool = False
    debug: bool = False

    model_config = SettingsConfigDict(env_prefix="ZEVON_", env_file=".env", extra="ignore")


settings = Settings()
