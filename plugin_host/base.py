from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .models import PluginManifest


class BasePlugin(ABC):
    """Host-side interface shared by process-backed plugins."""

    @property
    @abstractmethod
    def manifest(self) -> PluginManifest:
        raise NotImplementedError

    @property
    @abstractmethod
    def plugin_dir(self) -> Path:
        raise NotImplementedError

    @abstractmethod
    async def execute(
        self, arguments: dict[str, Any], workspace: Path
    ) -> tuple[dict[str, Any], float]:
        """Run the plugin and return (result data, duration in milliseconds)."""
        raise NotImplementedError

    def tool_definition(self) -> dict[str, Any]:
        """Expose manifest metadata in a common function-calling schema."""
        manifest = self.manifest
        return {
            "type": "function",
            "function": {
                "name": manifest.tool_name,
                "description": manifest.description,
                "parameters": manifest.input_schema,
            },
        }
