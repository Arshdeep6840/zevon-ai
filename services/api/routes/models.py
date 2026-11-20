"""Model management and hardware profile endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from packages.shared_schemas.models import ModelCard
from services.api.dependencies import get_gateway
from services.model_gateway.registry import HardwareProfile, ModelRegistry

router = APIRouter(prefix="/api/v1/models", tags=["Models"])


class SelectModelRequest(BaseModel):
    model_id: str


class OfflineToggleRequest(BaseModel):
    force_offline: bool


@router.get("", response_model=list[ModelCard])
async def list_models(gateway: ModelRegistry = Depends(get_gateway)):
    """List all available models with hardware fit and installation status."""
    return await gateway.list_models()


@router.get("/active", response_model=ModelCard)
async def get_active_model(gateway: ModelRegistry = Depends(get_gateway)):
    """Return currently active model."""
    active = await gateway.get_active_model()
    if not active:
        raise HTTPException(status_code=404, detail="No active model configured")
    return active


@router.post("/active")
async def set_active_model(
    payload: SelectModelRequest,
    gateway: ModelRegistry = Depends(get_gateway),
):
    """Switch active model and runtime adapter."""
    models = await gateway.list_models()
    matching = next((m for m in models if m.id == payload.model_id), None)
    if not matching:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{payload.model_id}' is not installed or available.",
        )
    gateway.set_active_model(payload.model_id)
    return {"status": "success", "active_model_id": payload.model_id}


@router.get("/hardware")
async def get_hardware_profile():
    """Scan local hardware and return memory, CPU cores, and recommended model tier."""
    return HardwareProfile.get_hardware_info()


@router.post("/offline-toggle")
async def toggle_offline_mode(
    payload: OfflineToggleRequest,
    gateway: ModelRegistry = Depends(get_gateway),
):
    """Toggle forced local-offline mode."""
    gateway.set_force_offline(payload.force_offline)
    return {"status": "success", "force_offline": payload.force_offline}
