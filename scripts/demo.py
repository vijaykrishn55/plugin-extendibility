
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from plugin_host import PluginRegistry


def main() -> int:
    parser = argparse.ArgumentParser(description="Plugin host demonstration")
    parser.add_argument(
        "--grant",
        action="append",
        default=[],
        help="Explicitly grant a permission, e.g. filesystem.read",
    )
    parser.add_argument("--tool", help="Optional tool to invoke")
    parser.add_argument(
        "--arguments",
        default='{"expression":"(150 + 50) * 3"}',
    )
    args = parser.parse_args()

    registry = PluginRegistry(
        ROOT / "plugins",
        ROOT / "workspace",
        set(args.grant),
    )

    print("Registered tools:")
    print(json.dumps(registry.tool_definitions(), indent=2))

    if registry.load_errors:
        print("Manifest errors:", json.dumps(registry.load_errors, indent=2))

    if args.tool:
        arguments = json.loads(args.arguments)
        result = asyncio.run(registry.execute(args.tool, arguments))
        print(result.model_dump_json(indent=2))
        return 0 if result.ok else 1

    calc = asyncio.run(
        registry.execute(
            "secure_calculator",
            {"expression": "(150 + 50) * 3"},
        )
    )
    read = asyncio.run(
        registry.execute("safe_file_reader", {"file_path": "notes.md"})
    )

    print("Calculator:", calc.model_dump_json())
    print("File reader:", read.model_dump_json())

    if not read.ok:
        error = str(read.error or "").lower()
        if "permission" in error or "filesystem.read" in error:
            print(
                "Grant filesystem.read to enable the file reader: "
                "--grant filesystem.read"
            )
        else:
            return 1

    return 0 if calc.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
