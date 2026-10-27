import json
from pathlib import Path
import tempfile

from plugin_host import PluginRegistry

ROOT = Path(__file__).resolve().parents[1]


def registry(grants=None):
    return PluginRegistry(ROOT / "plugins", ROOT / "workspace", set(grants or []))


def test_discovers_two_manifest_plugins():
    reg = registry()
    assert set(reg.plugins) == {"safe_file_reader", "secure_calculator"}
    assert reg.load_errors == []


def test_tool_definitions_have_json_schema():
    tools = registry().tool_definitions()
    assert len(tools) == 2
    calculator = next(t for t in tools if t["function"]["name"] == "secure_calculator")
    assert "expression" in calculator["function"]["parameters"]["properties"]


def test_reload_discovers_new_plugin_and_rejects_invalid_manifest():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        plugin = root / "plugins" / "new_tool"
        plugin.mkdir(parents=True)
        (plugin / "worker.py").write_text("print('{}')", encoding="utf-8")
        manifest = {"plugin_id": "new_tool", "tool_name": "new_tool",
                    "name": "New Tool", "version": "1.0", "description": "Test",
                    "entrypoint": "worker.py", "input_schema": {"type": "object", "properties": {},
                    "additionalProperties": False}}
        (plugin / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        reg = PluginRegistry(root / "plugins", root / "workspace")
        assert "new_tool" in reg.plugins
        (plugin / "manifest.json").write_text('{"bad": true}', encoding="utf-8")
        result = reg.reload()
        assert "new_tool" not in result["loaded"]
        assert len(result["errors"]) == 1


def test_duplicate_tool_name_is_rejected():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        plugins = root / "plugins"
        for plugin_id in ("first_plugin", "second_plugin"):
            plugin = plugins / plugin_id
            plugin.mkdir(parents=True)
            (plugin / "worker.py").write_text("print('{}')", encoding="utf-8")
            manifest = {"plugin_id": plugin_id, "tool_name": "duplicate_tool",
                        "name": plugin_id, "version": "1.0", "description": "Test",
                        "entrypoint": "worker.py", "input_schema": {"type": "object",
                        "properties": {}, "additionalProperties": False}}
            (plugin / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        reg = PluginRegistry(plugins, root / "workspace")
        assert list(reg.plugins) == ["duplicate_tool"]
        assert len(reg.load_errors) == 1
