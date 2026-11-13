"""Zevon AI backend. Run: uvicorn app.main:app --host 0.0.0.0 --port 8000"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import integrations
from .config import ROOT, Settings, settings as default_settings
from .core import voice
from .core.agent_engine import AgentEngine
from .core.llm import LLMProvider, make_provider
from .core.memory import Store
from .core.memory_tools import register_memory_tools
from .core.notify import Notifier
from .core.permissions import PermissionPolicy
from .core.tools import registry
from .core.vector_memory import VectorMemory
from .integrations.google import auth as google_auth
from .integrations.mcp_client import register_mcp
from .integrations.plugin_loader import load_plugins
from .scheduler.runner import ZevonScheduler
from .triggers.email_trigger import TRIGGER, EmailTrigger


class ChatIn(BaseModel):
    message: str
    session: str = "default"


class InstructionIn(BaseModel):
    name: str
    kind: str = "permanent"   # permanent | scheduled (schedule = cron) | conditional (schedule = "email:new")
    text: str
    schedule: str = ""


class KillIn(BaseModel):
    active: bool


class SpeakIn(BaseModel):
    text: str


class PushSub(BaseModel):
    endpoint: str
    keys: dict
    expirationTime: float | None = None


def create_app(cfg: Settings | None = None, llm: LLMProvider | None = None, start_scheduler: bool = True,
               vector: VectorMemory | None = None, load_extensions: bool = True) -> FastAPI:
    cfg = cfg or default_settings
    store = Store(cfg.db_path)
    policy = PermissionPolicy()
    vector = vector if vector is not None else VectorMemory.create(cfg)
    register_memory_tools(registry, store, vector)
    integrations.load_all()
    extras = {"extensions": [], "mcp": []}
    if load_extensions:
        extras["extensions"] = load_plugins(registry, store)
        extras["mcp"] = register_mcp(registry, store)
    notifier = Notifier(store, cfg)
    engine = AgentEngine(llm or make_provider(cfg), registry, store, policy, cfg.max_agent_steps)
    trigger = EmailTrigger(engine, store, notifier)
    scheduler = ZevonScheduler(engine, store, notifier) if start_scheduler else None

    @asynccontextmanager
    async def lifespan(app):
        if scheduler:
            scheduler.start()
            scheduler.add_interval(trigger.poll, cfg.email_poll_minutes, "email-trigger")
        yield
        if scheduler:
            scheduler.stop()

    app = FastAPI(title="Zevon AI", version="0.2.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=cfg.cors_origins, allow_methods=["*"],
                       allow_headers=["Authorization", "Content-Type"])

    def auth(authorization: str = Header(default="")):
        if cfg.api_token and authorization != f"Bearer {cfg.api_token}":
            raise HTTPException(401, "Invalid or missing token")

    api = Depends(auth)

    def features():
        return {"model": cfg.model, "kill_switch": policy.kill_switch, "auth_required": bool(cfg.api_token),
                "voice_stt": voice.stt_available(), "voice_tts": voice.tts_available(cfg),
                "vector_memory": vector is not None, "google": google_auth.configured(),
                "push": notifier.push_available(), "extensions": extras["extensions"], "mcp_tools": len(extras["mcp"]),
                "tools": len(registry.all())}

    @app.get("/api/health")
    def health():
        return {"status": "ok", **features()}

    @app.get("/api/capabilities", dependencies=[api])
    def capabilities():
        return features()

    @app.post("/api/chat", dependencies=[api])
    def chat(body: ChatIn):
        return engine.run(body.session, body.message)

    @app.get("/api/history", dependencies=[api])
    def history(session: str = "default"):
        return store.history(session, 50)

    @app.get("/api/tools", dependencies=[api])
    def tools():
        return [{"name": t.name, "description": t.description, "risk": t.risk} for t in registry.all()]

    # approvals
    @app.get("/api/approvals", dependencies=[api])
    def approvals(status: str = "pending"):
        return store.approvals(status)

    @app.post("/api/approvals/{aid}/approve", dependencies=[api])
    def approve(aid: int):
        try:
            return {"result": engine.approve(aid)}
        except KeyError as e:
            raise HTTPException(404, str(e))
        except PermissionError as e:
            raise HTTPException(423, str(e))

    @app.post("/api/approvals/{aid}/deny", dependencies=[api])
    def deny(aid: int):
        engine.deny(aid)
        return {"ok": True}

    @app.get("/api/audit", dependencies=[api])
    def audit(limit: int = 100):
        return store.audit_log(limit)

    @app.post("/api/kill", dependencies=[api])
    def kill(body: KillIn):
        policy.kill_switch = body.active
        store.audit("user", "kill_switch", body.active)
        return {"kill_switch": policy.kill_switch}

    # instructions
    @app.get("/api/instructions", dependencies=[api])
    def list_instructions():
        return store.instructions()

    @app.post("/api/instructions", dependencies=[api])
    def add_instruction(body: InstructionIn):
        if body.kind not in ("permanent", "scheduled", "conditional"):
            raise HTTPException(422, "kind must be permanent, scheduled or conditional")
        if body.kind == "conditional" and body.schedule != TRIGGER:
            raise HTTPException(422, f"conditional instructions need schedule='{TRIGGER}' (the only trigger so far)")
        iid = store.add_instruction(body.name, body.kind, body.text, body.schedule)
        if scheduler:
            scheduler.reload()
        return {"id": iid}

    @app.delete("/api/instructions/{iid}", dependencies=[api])
    def delete_instruction(iid: int):
        store.delete_instruction(iid)
        if scheduler:
            scheduler.reload()
        return {"ok": True}

    # notifications + web push
    @app.get("/api/notifications", dependencies=[api])
    def notifications(unread: bool = False):
        return store.notifications(unread_only=unread)

    @app.post("/api/notifications/read", dependencies=[api])
    def notifications_read():
        store.mark_notifications_read()
        return {"ok": True}

    @app.get("/api/push/public-key", dependencies=[api])
    def push_key():
        if not notifier.push_available():
            raise HTTPException(501, "Web Push not installed: pip install pywebpush")
        return {"key": notifier.public_key()}

    @app.post("/api/push/subscribe", dependencies=[api])
    def push_subscribe(sub: PushSub):
        store.add_push_sub(sub.endpoint, sub.model_dump())
        return {"ok": True}

    # voice
    @app.post("/api/voice/transcribe", dependencies=[api])
    async def transcribe(request: Request):
        if not voice.stt_available():
            raise HTTPException(501, "Speech-to-text not installed: pip install faster-whisper")
        audio = await request.body()
        if not audio:
            raise HTTPException(400, "Empty audio")
        return {"text": await run_in_threadpool(voice.transcribe, audio, cfg)}

    @app.post("/api/voice/speak", dependencies=[api])
    async def speak(body: SpeakIn):
        if not voice.tts_available(cfg):
            raise HTTPException(501, "Piper TTS not configured: pip install piper-tts and set ZEVON_PIPER_MODEL")
        wav = await run_in_threadpool(voice.synthesize, body.text, cfg)
        return Response(wav, media_type="audio/wav")

    app.state.engine, app.state.store, app.state.notifier, app.state.trigger = engine, store, notifier, trigger
    dist, legacy = Path(ROOT / "frontend" / "dist"), Path(ROOT / "frontend" / "legacy")
    ui = dist if dist.exists() else legacy
    if ui.exists():
        app.mount("/", StaticFiles(directory=str(ui), html=True), name="frontend")
    return app


app = create_app()
