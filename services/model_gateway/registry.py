"""Model Registry and Orchestration Gateway for local model providers."""

import os
from typing import AsyncIterator, Dict, List, Optional, Any
from packages.shared_schemas.models import Message, ModelCard
from .base import BaseModelProvider
from .ollama import OllamaProvider
from .offline_mock import OfflineMockProvider


class HardwareProfile:
    @staticmethod
    def get_hardware_info() -> Dict[str, Any]:
        """Detect local CPU cores, RAM, and recommend model parameters."""
        ram_gb = 8.0
        cpu_count = os.cpu_count() or 4
        try:
            import psutil
            ram_bytes = psutil.virtual_memory().total
            ram_gb = round(ram_bytes / (1024**3), 1)
        except Exception:
            pass

        if ram_gb < 12.0:
            recommended_tier = "compact"
            recommended_param_size = "1B - 3B"
            description = "Low-memory footprint; optimized for fast CPU inference and compact models."
        elif ram_gb < 24.0:
            recommended_tier = "balanced"
            recommended_param_size = "7B - 8B"
            description = "Standard desktop profile; capable of running 7B-8B quantized models smoothly."
        else:
            recommended_tier = "performance"
            recommended_param_size = "14B - 32B"
            description = "High-memory workstation; capable of running large models and deep reasoning tasks."

        return {
            "ram_gb": ram_gb,
            "cpu_cores": cpu_count,
            "tier": recommended_tier,
            "recommended_param_size": recommended_param_size,
            "description": description,
        }

    @staticmethod
    def assess_model_fit(model: ModelCard, ram_gb: float) -> str:
        """Rate model suitability for current hardware."""
        param = model.parameter_size.lower()
        if any(p in param for p in ["1b", "2b", "3b", "compact", "simulated"]):
            return "optimal"
        elif any(p in param for p in ["7b", "8b"]):
            return "optimal" if ram_gb >= 12.0 else "heavy"
        elif any(p in param for p in ["14b", "32b", "70b"]):
            return "optimal" if ram_gb >= 30.0 else "heavy"
        return "compatible"


class ModelRegistry:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.providers: Dict[str, BaseModelProvider] = {
            "offline-embedded": OfflineMockProvider(),
            "ollama": OllamaProvider(base_url=ollama_url),
        }
        self.active_model_id: str = "zevon-offline-compact"
        self.force_offline: bool = False

    def register_provider(self, name: str, provider: BaseModelProvider) -> None:
        self.providers[name] = provider

    def set_active_model(self, model_id: str) -> bool:
        self.active_model_id = model_id
        return True

    def set_force_offline(self, enabled: bool) -> None:
        self.force_offline = enabled

    async def list_models(self) -> List[ModelCard]:
        hw = HardwareProfile.get_hardware_info()
        ram_gb = hw["ram_gb"]

        all_models: List[ModelCard] = []
        # If force_offline is true, only return offline-embedded
        for provider_name, provider in self.providers.items():
            if self.force_offline and provider_name != "offline-embedded":
                continue
            try:
                models = await provider.list_models()
                for m in models:
                    m.is_active = (m.id == self.active_model_id)
                    fit = HardwareProfile.assess_model_fit(m, ram_gb)
                    # Enrich description with fit rating if not present
                    if not m.description:
                        m.description = f"Hardware fit: {fit}"
                    all_models.append(m)
            except Exception:
                continue

        # If active model was not found in list, default back to offline compact
        if not any(m.is_active for m in all_models) and all_models:
            all_models[0].is_active = True
            self.active_model_id = all_models[0].id

        return all_models

    async def get_active_model(self) -> Optional[ModelCard]:
        models = await self.list_models()
        for m in models:
            if m.id == self.active_model_id:
                return m
        return models[0] if models else None

    async def check_health(self) -> Dict[str, Any]:
        hw = HardwareProfile.get_hardware_info()
        provider_health = {}
        for name, provider in self.providers.items():
            try:
                provider_health[name] = await provider.check_health()
            except Exception:
                provider_health[name] = False

        is_ollama_ready = provider_health.get("ollama", False)
        mode = "offline" if (self.force_offline or not is_ollama_ready) else "local-connected"

        return {
            "status": "ok",
            "mode": mode,
            "force_offline": self.force_offline,
            "active_model_id": self.active_model_id,
            "providers": provider_health,
            "hardware": hw,
        }

    async def stream_chat(
        self,
        messages: List[Message],
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        target_model_id = model_name or self.active_model_id

        # Determine target provider
        selected_provider: Optional[BaseModelProvider] = None
        if not self.force_offline:
            # Check if model exists in Ollama
            ollama_provider = self.providers.get("ollama")
            if ollama_provider and await ollama_provider.check_health():
                ollama_models = await ollama_provider.list_models()
                if any(m.id == target_model_id for m in ollama_models):
                    selected_provider = ollama_provider

        # Fallback to offline mock provider
        if not selected_provider:
            selected_provider = self.providers.get("offline-embedded")

        if not selected_provider:
            raise RuntimeError("No suitable model provider available.")

        async for chunk in selected_provider.stream_chat(
            messages=messages,
            model_name=target_model_id,
            temperature=temperature,
            tools=tools,
        ):
            yield chunk


_global_registry: Optional[ModelRegistry] = None


def get_model_registry(ollama_url: str = "http://localhost:11434") -> ModelRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = ModelRegistry(ollama_url=ollama_url)
    return _global_registry
