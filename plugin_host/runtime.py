from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from .base import BasePlugin
from .models import InvocationRequest, PluginManifest, WorkerResponse


class WorkerFailure(RuntimeError):
    pass


class WorkerTimeout(WorkerFailure):
    pass


def clean_environment() -> dict[str, str]:
    """Retain only OS variables needed to launch Python; never forward secrets."""
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR"}
    return {key: value for key, value in os.environ.items() if key.upper() in allowed}


def resolve_entrypoint(plugin_dir: Path, manifest: PluginManifest) -> Path:
    root = plugin_dir.resolve()
    entry = (root / manifest.entrypoint).resolve()
    if not entry.is_relative_to(root) or not entry.is_file():
        raise ValueError("Plugin entrypoint must be an existing file inside its plugin folder")
    return entry


async def run_worker(
    plugin_dir: Path,
    manifest: PluginManifest,
    workspace: Path,
    arguments: dict[str, Any],
    max_output_bytes: int = 1_000_000,
) -> tuple[dict[str, Any], float]:
    entry = resolve_entrypoint(plugin_dir, manifest)
    request = InvocationRequest(
        jsonrpc="2.0",
        id=1,
        method="plugin.execute",
        params={"tool_name": manifest.tool_name, "arguments": arguments,
                 "workspace": str(workspace.resolve()),
                 "permissions": manifest.permissions},
    )
    started = time.perf_counter()
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-I", str(entry),
        cwd=str(plugin_dir), env=clean_environment(),
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    payload = request.model_dump_json().encode("utf-8")
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(payload), timeout=manifest.timeout_seconds
        )
    except asyncio.TimeoutError as exc:
        process.kill()
        await process.wait()
        raise WorkerTimeout(
            f"Plugin exceeded {manifest.timeout_seconds:.1f}s timeout"
        ) from exc
    duration_ms = (time.perf_counter() - started) * 1000
    if len(stdout) > max_output_bytes:
        raise WorkerFailure(f"Plugin output exceeded {max_output_bytes} bytes")
    if process.returncode != 0:
        detail = stderr.decode("utf-8", errors="replace")[-2000:]
        raise WorkerFailure(f"Worker exited with code {process.returncode}: {detail}")
    try:
        response = WorkerResponse.model_validate_json(stdout)
    except Exception as exc:
        raise WorkerFailure(f"Worker returned invalid JSON-RPC response: {exc}") from exc
    if response.id != request.id:
        raise WorkerFailure("Worker response id did not match request id")
    if response.error is not None:
        message = str(response.error.get("message", "Plugin execution failed"))
        if response.error.get("code") == -32003:
            raise PermissionError(message)
        if response.error.get("code") == -32602:
            raise ValueError(message)
        raise WorkerFailure(message)
    if response.result is None:
        raise WorkerFailure("Worker response had no result")
    return response.result, duration_ms


class WorkerPlugin(BasePlugin):
    """Concrete BasePlugin that runs an entrypoint in an isolated subprocess."""

    def __init__(self, manifest: PluginManifest, plugin_dir: Path) -> None:
        self._manifest = manifest
        self._plugin_dir = plugin_dir.resolve()

    @property
    def manifest(self) -> PluginManifest:
        return self._manifest

    @property
    def plugin_dir(self) -> Path:
        return self._plugin_dir

    async def execute(
        self, arguments: dict[str, Any], workspace: Path
    ) -> tuple[dict[str, Any], float]:
        return await run_worker(self.plugin_dir, self.manifest, workspace, arguments)
