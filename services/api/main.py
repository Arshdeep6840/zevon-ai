"""FastAPI entrypoint and application factory for Zevon."""

from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from services.api.config import settings
from services.api.routes import chat, conversations, health, models, realtime, voice
from services.api.routes import settings as settings_routes
from services.memory.database import init_db

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle handler."""
    # Ensure database initialized on startup
    await init_db(settings.db_path)
    print(f"[*] Zevon initialized with database at: {settings.db_path}")
    print(f"[*] Serving web UI at: http://{settings.host}:{settings.port}/")
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Local-first, voice-enabled personal AI assistant runtime.",
    lifespan=lifespan,
)

# CORS configuration for desktop (Tauri) and local browser clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 Routers
app.include_router(health.router)
app.include_router(models.router)
app.include_router(conversations.router)
app.include_router(settings_routes.router)
app.include_router(chat.router)
app.include_router(realtime.router)
app.include_router(voice.router)

# Mount Static Assets and Web UI
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    """Serve the single-page web chat application."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Zevon API running. Static UI not found."}


def start():
    """Run server via CLI command."""
    uvicorn.run(
        "services.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    start()
