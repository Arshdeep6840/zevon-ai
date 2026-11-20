"""Model Registry and Orchestration Gateway for local model providers."""

import os
from collections.abc import AsyncIterator
from typing import Any

from packages.shared_schemas.models import Message, ModelCard

from .base import BaseModelProvider
from .offline_mock import OfflineMockProvider
from .ollama import OllamaProvider


class HardwareProfile:
    @staticmethod
    def get_hardware_info() -> dict[str, Any]:
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
            description = (
                "Low-memory footprint; optimized for fast CPU inference and compact models."
            )
        elif ram_gb < 24.0:
            recommended_tier = "balanced"
            recommended_param_size = "7B - 8B"
            description = (
                "Standard desktop profile; capable of running 7B-8B quantized models smoothly."
            )
        else:
            recommended_tier = "performance"
            recommended_param_size = "14B - 32B"
            description = (
                "High-memory workstation; capable of running large models and deep reasoning tasks."
            )

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
        self.providers: dict[str, BaseModelProvider] = {
            "ollama": OllamaProvider(base_url=ollama_url),
            "offline-embedded": OfflineMockProvider(),
        }
        self.active_model_id: str | None = None
        self._user_selected: bool = False
        self.force_offline: bool = False

    def register_provider(self, name: str, provider: BaseModelProvider) -> None:
        self.providers[name] = provider

    def set_active_model(self, model_id: str) -> bool:
        self.active_model_id = model_id
        self._user_selected = True
        return True

    def set_force_offline(self, enabled: bool) -> None:
        self.force_offline = enabled

    def update_ollama_url(self, ollama_url: str) -> None:
        if "ollama" in self.providers and hasattr(self.providers["ollama"], "set_base_url"):
            self.providers["ollama"].set_base_url(ollama_url)

    async def list_models(self) -> list[ModelCard]:
        hw = HardwareProfile.get_hardware_info()
        ram_gb = hw["ram_gb"]

        all_models: list[ModelCard] = []
        # If force_offline is true, only return offline-embedded
        for provider_name, provider in self.providers.items():
            if self.force_offline and provider_name != "offline-embedded":
                continue
            try:
                models = await provider.list_models()
                for m in models:
                    fit = HardwareProfile.assess_model_fit(m, ram_gb)
                    if not m.description:
                        m.description = f"Hardware fit: {fit}"
                    all_models.append(m)
            except Exception:
                continue

        # If user has not explicitly locked an active model, auto-select the best available
        if not self._user_selected or not self.active_model_id:
            ollama_models = [m for m in all_models if m.provider == "ollama"]
            if ollama_models and not self.force_offline:
                self.active_model_id = ollama_models[0].id
            elif all_models:
                self.active_model_id = all_models[0].id

        for m in all_models:
            m.is_active = m.id == self.active_model_id

        # If active model was not found in list, default back to first available
        if not any(m.is_active for m in all_models) and all_models:
            all_models[0].is_active = True
            self.active_model_id = all_models[0].id

        return all_models

    async def get_active_model(self) -> ModelCard | None:
        models = await self.list_models()
        for m in models:
            if m.id == self.active_model_id:
                return m
        return models[0] if models else None

    async def get_active_provider(self) -> BaseModelProvider | None:
        """Return the active model provider (Ollama if available, otherwise offline embedded)."""
        if not self.force_offline:
            ollama_provider = self.providers.get("ollama")
            if ollama_provider and await ollama_provider.check_health():
                return ollama_provider
        return self.providers.get("offline-embedded")

    async def check_health(self) -> dict[str, Any]:
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
        messages: list[Message],
        model_name: str | None = None,
        temperature: float = 0.7,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]:
        target_model_id = model_name or self.active_model_id
        if not target_model_id:
            active_card = await self.get_active_model()
            if active_card:
                target_model_id = active_card.id

        # Determine target provider
        selected_provider: BaseModelProvider | None = None
        if not self.force_offline:
            # Check if model exists in Ollama
            ollama_provider = self.providers.get("ollama")
            if ollama_provider and await ollama_provider.check_health():
                ollama_models = await ollama_provider.list_models()
                if any(m.id == target_model_id for m in ollama_models):
                    selected_provider = ollama_provider
                elif ollama_models:
                    selected_provider = ollama_provider
                    target_model_id = ollama_models[0].id

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


_global_registry: ModelRegistry | None = None


def get_model_registry(ollama_url: str = "http://localhost:11434") -> ModelRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = ModelRegistry(ollama_url=ollama_url)
    return _global_registry
