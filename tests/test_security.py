import asyncio
from pathlib import Path

from plugin_host import PluginRegistry

ROOT = Path(__file__).resolve().parents[1]


def call(tool, args, grants=None):
    reg = PluginRegistry(ROOT / "plugins", ROOT / "workspace", set(grants or []))
    return asyncio.run(reg.execute(tool, args))


def test_safe_calculation():
    result = call("secure_calculator", {"expression": "(150 + 50) * 3"})
    assert result.ok and result.result["value"] == 600


def test_calculator_rejects_code_injection():
    result = call("secure_calculator", {"expression": "__import__('os').system('whoami')"})
    assert not result.ok


def test_calculator_rejects_names_and_comprehensions():
    result = call("secure_calculator", {"expression": "open('secret.txt').read()"})
    assert not result.ok


def test_file_reader_requires_explicit_permission():
    result = call("safe_file_reader", {"file_path": "notes.md"})
    assert not result.ok and result.error["code"] == "PERMISSION_DENIED"


def test_file_reader_reads_workspace_file():
    result = call("safe_file_reader", {"file_path": "notes.md"}, ["filesystem.read"])
    assert result.ok and "Plugin workspace sample" in result.result["content"]


def test_file_reader_blocks_traversal():
    result = call("safe_file_reader", {"file_path": "../../pyproject.toml"}, ["filesystem.read"])
    assert not result.ok and result.error["code"] == "PERMISSION_DENIED"


def test_validation_rejects_extra_arguments():
    result = call("secure_calculator", {"expression": "2+2", "danger": True})
    assert not result.ok and result.error["code"] == "INVALID_ARGUMENTS"


def test_unknown_tool_fails_gracefully():
    result = call("missing_tool", {})
    assert not result.ok and result.error["code"] == "UNKNOWN_TOOL"
