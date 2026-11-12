"""OpenJarvis AI backend. Run: uvicorn app.main:app --host 0.0.0.0 --port 8000"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import integrations
from .config import Settings, settings as default_settings
from .core.agent_engine import AgentEngine
from .core.llm import LLMProvider, make_provider
from .core.memory import Store
from .core.memory_tools import register_memory_tools
from .core.permissions import PermissionPolicy
from .core.tools import registry
from .scheduler.runner import JarvisScheduler


class ChatIn(BaseModel):
    message: str
    session: str = "default"


class InstructionIn(BaseModel):
    name: str
    kind: str = "permanent"      # permanent | scheduled | conditional
    text: str
    schedule: str = ""           # cron for scheduled, e.g. "0 8 * * *"


class KillIn(BaseModel):
    active: bool


def create_app(cfg: Settings | None = None, llm: LLMProvider | None = None, start_scheduler: bool = True) -> FastAPI:
    cfg = cfg or default_settings
    store = Store(cfg.db_path)
    policy = PermissionPolicy()
    register_memory_tools(registry, store)
    integrations.load_all()
    engine = AgentEngine(llm or make_provider(cfg), registry, store, policy, cfg.max_agent_steps)
    scheduler = JarvisScheduler(engine, store) if start_scheduler else None

    @asynccontextmanager
    async def lifespan(app):
        if scheduler:
            scheduler.start()
        yield
        if scheduler:
            scheduler.stop()

    app = FastAPI(title="OpenJarvis AI", version="0.1.0", lifespan=lifespan)

    def auth(authorization: str = Header(default="")):
        if cfg.api_token and authorization != f"Bearer {cfg.api_token}":
            raise HTTPException(401, "Invalid or missing token")

    api = Depends(auth)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "model": cfg.model, "kill_switch": policy.kill_switch,
                "auth_required": bool(cfg.api_token)}

    @app.post("/api/chat", dependencies=[api])
    def chat(body: ChatIn):
        return engine.run(body.session, body.message)

    @app.get("/api/history", dependencies=[api])
    def history(session: str = "default"):
        return store.history(session, 50)

    @app.get("/api/tools", dependencies=[api])
    def tools():
        return [{"name": t.name, "description": t.description, "risk": t.risk} for t in registry.all()]

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

    @app.get("/api/instructions", dependencies=[api])
    def list_instructions():
        return store.instructions()

    @app.post("/api/instructions", dependencies=[api])
    def add_instruction(body: InstructionIn):
        if body.kind not in ("permanent", "scheduled", "conditional"):
            raise HTTPException(422, "kind must be permanent, scheduled or conditional")
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

    app.state.engine, app.state.store = engine, store
    app.mount("/", StaticFiles(directory=cfg.frontend_dir, html=True), name="frontend")
    return app


app = create_app()
