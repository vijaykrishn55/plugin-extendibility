from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from pydantic import ValidationError

from .arguments import validate_with_pydantic
from .models import PluginCallResult, PluginManifest
from .runtime import WorkerFailure, WorkerPlugin, WorkerTimeout


class PluginRegistry:
    """Discover manifests, publish tool schemas, validate and dispatch calls."""

    def __init__(self, plugin_dir: Path, workspace: Path,
                 granted_permissions: set[str] | None = None) -> None:
        self.plugin_dir = Path(plugin_dir).resolve()
        self.workspace = Path(workspace).resolve()
        self.granted_permissions = set(granted_permissions or set())
        self.plugins: dict[str, WorkerPlugin] = {}
        self.load_errors: list[dict[str, str]] = []
        self.reload()

    def reload(self) -> dict[str, Any]:
        """Reload manifests without restarting the host; invalid ones are skipped."""
        loaded: dict[str, WorkerPlugin] = {}
        errors: list[dict[str, str]] = []
        for manifest_path in sorted(self.plugin_dir.glob("*/manifest.json")):
            plugin_dir = manifest_path.parent.resolve()
            try:
                raw = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest = PluginManifest.model_validate(raw)
                if not manifest.enabled:
                    continue
                Draft202012Validator.check_schema(manifest.input_schema)
                if manifest.tool_name in loaded:
                    raise ValueError(f"Duplicate tool name: {manifest.tool_name}")
                entry = (plugin_dir / manifest.entrypoint).resolve()
                if not entry.is_relative_to(plugin_dir) or not entry.is_file():
                    raise ValueError("Entrypoint must exist inside plugin folder")
                loaded[manifest.tool_name] = WorkerPlugin(manifest, plugin_dir)
            except Exception as exc:
                errors.append({"manifest": str(manifest_path), "error": str(exc)})
        self.plugins = loaded
        self.load_errors = errors
        return {"loaded": list(loaded), "errors": errors}

    def tool_definitions(self) -> list[dict[str, Any]]:
        """Return OpenAI-compatible JSON Schema tool definitions."""
        return [plugin.tool_definition() for plugin in self.plugins.values()]

    async def execute(self, tool_name: str, arguments: Any) -> PluginCallResult:
        started = time.perf_counter()
        try:
            if tool_name not in self.plugins:
                raise KeyError(f"Unknown plugin tool: {tool_name}")
            plugin = self.plugins[tool_name]
            manifest = plugin.manifest
            missing = set(manifest.permissions) - self.granted_permissions
            if missing:
                raise PermissionError(f"Permission not granted: {', '.join(sorted(missing))}")
            if not isinstance(arguments, dict):
                raise ValueError("Tool arguments must be a JSON object")
            typed_args = validate_with_pydantic(tool_name, arguments)
            payload_args = typed_args if typed_args is not None else arguments
            Draft202012Validator(manifest.input_schema).validate(payload_args)
            result, duration = await plugin.execute(payload_args, self.workspace)
            return PluginCallResult(ok=True, tool_name=tool_name,
                                    result=result, duration_ms=duration)
        except ValidationError as exc:
            error = {"code": "INVALID_ARGUMENTS", "message": str(exc.errors())}
        except Exception as exc:
            code = "TIMEOUT" if isinstance(exc, WorkerTimeout) else "EXECUTION_ERROR"
            if isinstance(exc, PermissionError):
                code = "PERMISSION_DENIED"
            elif isinstance(exc, KeyError):
                code = "UNKNOWN_TOOL"
            elif isinstance(exc, ValueError):
                code = "INVALID_ARGUMENTS"
            error = {"code": code, "message": str(exc)}
        return PluginCallResult(ok=False, tool_name=tool_name, error=error,
                                duration_ms=(time.perf_counter() - started) * 1000)
