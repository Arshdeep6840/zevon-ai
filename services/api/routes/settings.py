"""User preferences, system configuration, and persona profile endpoints."""

from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from packages.shared_schemas.profiles import (
    ProfileDefinition,
    get_profile,
    list_profiles,
    PROFILES,
)
from services.api.dependencies import get_repository, get_gateway
from services.memory.repository import MemoryRepository
from services.model_gateway.registry import ModelRegistry
from services.api.config import settings

router = APIRouter(prefix="/api/v1", tags=["Settings & Profiles"])


class UpdateSettingsRequest(BaseModel):
    settings: Dict[str, str]


@router.get("/profiles", response_model=List[ProfileDefinition])
async def get_profiles():
    """List available persona profiles (Personal, Developer, Business, Creator)."""
    return list_profiles()


@router.get("/profiles/{profile_id}", response_model=ProfileDefinition)
async def get_profile_by_id(profile_id: str):
    """Retrieve details, system prompt, and starter templates for a profile."""
    if profile_id.lower() not in PROFILES:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")
    return get_profile(profile_id)


@router.get("/settings")
async def get_all_settings(
    repo: MemoryRepository = Depends(get_repository),
    gateway: ModelRegistry = Depends(get_gateway),
):
    """Retrieve all persisted user settings and defaults."""
    db_settings = await repo.get_all_settings()
    active_model = await gateway.get_active_model()

    return {
        "active_profile": db_settings.get("active_profile", settings.default_profile),
        "active_model_id": active_model.id if active_model else settings.default_model,
        "force_offline": gateway.force_offline,
        "theme": db_settings.get("theme", "dark"),
        "user_name": db_settings.get("user_name", "User"),
        "ollama_url": settings.ollama_url,
        "all_custom": db_settings,
    }


@router.post("/settings")
async def update_settings(
    payload: UpdateSettingsRequest,
    repo: MemoryRepository = Depends(get_repository),
    gateway: ModelRegistry = Depends(get_gateway),
):
    """Persist updated user settings."""
    for key, value in payload.settings.items():
        await repo.set_setting(key, value)
        if key == "active_model_id":
            gateway.set_active_model(value)
        elif key == "force_offline":
            gateway.set_force_offline(value.lower() == "true")

    return {"status": "success", "updated_keys": list(payload.settings.keys())}
