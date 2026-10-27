import asyncio
import json
from pathlib import Path
import tempfile

from plugin_host import PluginRegistry

ROOT = Path(__file__).resolve().parents[1]


def test_plugin_timeout_is_enforced():
    with tempfile.TemporaryDirectory() as folder:
        base = Path(folder)
        plugin = base / "plugins" / "sleeper"
        plugin.mkdir(parents=True)
        (plugin / "worker.py").write_text(
            "import time\ntime.sleep(5)\nprint('{}')\n", encoding="utf-8")
        manifest = {"plugin_id": "sleeper", "tool_name": "sleeper_tool",
                    "name": "Sleeper", "version": "1.0", "description": "Timeout test",
                    "entrypoint": "worker.py", "input_schema": {"type": "object",
                    "properties": {}, "additionalProperties": False}, "timeout_seconds": 0.2}
        (plugin / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        reg = PluginRegistry(base / "plugins", base / "workspace")
        result = asyncio.run(reg.execute("sleeper_tool", {}))
        assert not result.ok and result.error["code"] == "TIMEOUT"


def test_entrypoint_cannot_escape_plugin_directory():
    with tempfile.TemporaryDirectory() as folder:
        base = Path(folder)
        plugin = base / "plugins" / "bad"
        plugin.mkdir(parents=True)
        (base / "outside.py").write_text("print('{}')", encoding="utf-8")
        manifest = {"plugin_id": "bad_plugin", "tool_name": "bad_tool", "name": "Bad",
                    "version": "1.0", "description": "Invalid entrypoint", "entrypoint": "../outside.py",
                    "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}}
        (plugin / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        reg = PluginRegistry(base / "plugins", base / "workspace")
        assert "bad_tool" not in reg.plugins
        assert reg.load_errors
