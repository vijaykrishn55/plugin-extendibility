from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PluginManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plugin_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    tool_name: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    name: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=32)
    description: str = Field(min_length=1, max_length=500)
    entrypoint: str = Field(min_length=1, max_length=200)
    input_schema: dict[str, Any]
    permissions: list[str] = Field(default_factory=list)
    timeout_seconds: float = Field(default=10.0, gt=0, le=30)
    enabled: bool = True

    @field_validator("entrypoint")
    @classmethod
    def relative_entrypoint(cls, value: str) -> str:
        from pathlib import PurePosixPath
        path = PurePosixPath(value.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("entrypoint must be a relative path inside the plugin folder")
        return path.as_posix()


class InvocationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jsonrpc: Literal["2.0"]
    id: int | str
    method: Literal["plugin.execute"]
    params: dict[str, Any]


class WorkerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jsonrpc: Literal["2.0"]
    id: int | str
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


class PluginCallResult(BaseModel):
    ok: bool
    tool_name: str
    result: Any = None
    error: dict[str, Any] | None = None
    duration_ms: float = 0.0
