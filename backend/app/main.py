"""Zevon AI backend. Run: uvicorn app.main:app --host 0.0.0.0 --port 8000"""
import json
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
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
from .core.permissions import DEFAULT_BY_RISK, Decision, PermissionPolicy
from .core.tools import registry
from .core.vector_memory import VectorMemory
from .integrations.google import auth as google_auth
from .integrations.mcp_client import register_mcp
from .integrations.plugin_loader import load_plugins
from .scheduler.runner import ZevonScheduler
from .triggers import TRIGGER_HELP, valid_trigger
from .triggers.email_trigger import TRIGGER, EmailTrigger
from .triggers.sources import CalendarTrigger, FileTrigger, SlackTrigger, TimeTrigger


class ChatIn(BaseModel):
    message: str
    session: str = "default"


class InstructionIn(BaseModel):
    name: str
    kind: str = "permanent"   # permanent | scheduled (schedule = cron) | conditional (schedule = "email:new")
    text: str
    schedule: str = ""


class EnabledIn(BaseModel):
    enabled: bool


class MemoryIn(BaseModel):
    text: str


class PolicyIn(BaseModel):
    decision: str     # allow | approve | deny | default


class FcmIn(BaseModel):
    token: str


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
    policy.overrides = {t: Decision(d) for t, d in store.tool_policies().items()}
    provider = llm or make_provider(cfg)
    engine = AgentEngine(provider, registry, store, policy, cfg.max_agent_steps, cfg.history_keep,
                         cfg.summarize_after, cfg.planning)
    trigger = EmailTrigger(engine, store, notifier)
    other_triggers = [T(engine, store, notifier) for T in (CalendarTrigger, FileTrigger, SlackTrigger, TimeTrigger)]
    scheduler = ZevonScheduler(engine, store, notifier) if start_scheduler else None

    @asynccontextmanager
    async def lifespan(app):
        if scheduler:
            scheduler.start()
            scheduler.add_interval(trigger.poll, cfg.email_poll_minutes, "email-trigger")
            for t in other_triggers:
                scheduler.add_interval(t.poll, cfg.trigger_poll_minutes, f"trigger-{t.name}")
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
                "tools": len(registry.all()),
                "provider": provider.name, "local_model": provider.local, "fcm": notifier.fcm_available(),
                "planning": cfg.planning, "terminal_ask": cfg.terminal_ask.lower() in ("on", "1", "true", "yes"),
                "playwright": __import__("importlib.util").util.find_spec("playwright") is not None}

    @app.get("/api/health")
    def health():
        return {"status": "ok", **features()}

    @app.get("/api/capabilities", dependencies=[api])
    def capabilities():
        return features()

    @app.post("/api/chat", dependencies=[api])
    def chat(body: ChatIn):
        return engine.run(body.session, body.message)

    @app.post("/api/chat/stream", dependencies=[api])
    def chat_stream(body: ChatIn):
        def gen():
            try:
                for ev in engine.run_stream(body.session, body.message):
                    yield f"data: {json.dumps(ev, default=str)}\n\n"
            except Exception as e:  # keep the stream well-formed for the client
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.get("/api/sessions", dependencies=[api])
    def sessions():
        return store.sessions()

    @app.delete("/api/sessions/{sid}", dependencies=[api])
    def delete_session(sid: str):
        store.delete_session(sid)
        return {"ok": True}

    # memories (view / add / edit / delete)
    @app.get("/api/memories", dependencies=[api])
    def memories(q: str = ""):
        return store.memories(q, limit=200)

    @app.post("/api/memories", dependencies=[api])
    def add_memory(body: MemoryIn):
        mid = store.remember(body.text.strip())
        if vector:
            try:
                vector.add(mid, body.text)
            except Exception as e:
                store.audit("memory", "vector_add", str(e)[:200], "failed")
        return {"id": mid}

    @app.put("/api/memories/{mid}", dependencies=[api])
    def edit_memory(mid: int, body: MemoryIn):
        if not store.get_memory(mid):
            raise HTTPException(404, "No such memory")
        store.update_memory(mid, body.text.strip())
        if vector:
            try:
                vector.add(mid, body.text)   # upsert re-embeds
            except Exception as e:
                store.audit("memory", "vector_update", str(e)[:200], "failed")
        return {"ok": True}

    @app.delete("/api/memories/{mid}", dependencies=[api])
    def delete_memory(mid: int):
        store.delete_memory(mid)
        if vector:
            try:
                vector.delete(mid)
            except Exception as e:
                store.audit("memory", "vector_delete", str(e)[:200], "failed")
        return {"ok": True}

    # per-tool permission settings (only the owner can change these; the agent has no tool for it)
    @app.get("/api/policies", dependencies=[api])
    def policies():
        out = []
        for t in registry.all():
            default = DEFAULT_BY_RISK[t.risk].value
            ov = policy.overrides.get(t.name)
            out.append({"name": t.name, "description": t.description, "risk": t.risk, "default": default,
                        "override": ov.value if ov else None, "effective": (ov.value if ov else default)})
        return out

    @app.put("/api/policies/{tool}", dependencies=[api])
    def set_policy(tool: str, body: PolicyIn):
        if registry.get(tool) is None:
            raise HTTPException(404, "Unknown tool")
        if body.decision == "default":
            store.clear_tool_policy(tool)
            policy.overrides.pop(tool, None)
        elif body.decision in ("allow", "approve", "deny"):
            store.set_tool_policy(tool, body.decision)
            policy.overrides[tool] = Decision(body.decision)
        else:
            raise HTTPException(422, "decision must be allow, approve, deny or default")
        store.audit("user", "tool_policy", f"{tool} -> {body.decision}")
        return {"ok": True}

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
        if body.kind == "conditional" and not valid_trigger(body.schedule):
            raise HTTPException(422, f"conditional instructions need a trigger like: {', '.join(TRIGGER_HELP)}")
        iid = store.add_instruction(body.name, body.kind, body.text, body.schedule)
        if scheduler:
            scheduler.reload()
        return {"id": iid}

    @app.get("/api/triggers", dependencies=[api])
    def triggers():
        return [{"trigger": k, "help": v} for k, v in TRIGGER_HELP.items()]

    @app.patch("/api/instructions/{iid}", dependencies=[api])
    def toggle_instruction(iid: int, body: EnabledIn):
        store.set_instruction_enabled(iid, body.enabled)
        if scheduler:
            scheduler.reload()
        return {"ok": True}

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

    @app.post("/api/push/fcm", dependencies=[api])
    def push_fcm(body: FcmIn):
        store.add_fcm_token(body.token)
        return {"ok": True}

    @app.get("/api/screenshots/{name}", dependencies=[api])
    def screenshot(name: str):
        if not re.fullmatch(r"[a-f0-9]{12}\.png", name):
            raise HTTPException(404, "Not found")
        f = Path(cfg.screenshots_dir) / name
        if not f.exists():
            raise HTTPException(404, "Not found")
        return FileResponse(str(f), media_type="image/png")

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
