# Plugins & Extensibility

A manifest-driven plugin host with dynamic discovery, JSON Schema tool definitions, Pydantic validation, permission checks, and cross-platform subprocess execution.

## Architecture

- `plugin_host/base.py`: abstract `BasePlugin` interface for plugin implementations.
- `plugin_host/models.py`: validated manifests, IPC envelopes, and results.
- `plugin_host/registry.py`: discovery, hot reload, schema validation, permissions, and dispatch.
- `plugin_host/runtime.py`: subprocess-backed `WorkerPlugin`, JSON-RPC stdio IPC, timeouts, and environment filtering.
- `plugins/safe_file_reader/`: workspace-only file reader.
- `plugins/secure_calculator/`: AST-based arithmetic evaluator that does not use `eval`.
- `tests/`: lifecycle, schema, security, and timeout tests.

## Run

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/verify.py
```

## Demo

```bash
python scripts/demo.py
python scripts/demo.py --grant filesystem.read
python scripts/demo.py --tool secure_calculator --arguments '{"expression":"(150 + 50) * 3"}'
python scripts/demo.py --grant filesystem.read --tool safe_file_reader --arguments '{"file_path":"notes.md"}'
```

## Plugin manifests

Each folder under `plugins/` has a `manifest.json` declaring metadata, an entrypoint, permissions, a timeout, and an input JSON Schema. `PluginRegistry.reload()` rediscovers plugins without restarting the host. Invalid manifests are skipped and reported in `load_errors`; duplicate active tool names are rejected.

Workers communicate through a single JSON-RPC 2.0 request and response over stdin/stdout. Keep stdout reserved for the protocol; write diagnostics to stderr.

## Security notes

The host validates manifests and arguments, checks declared permissions, restricts the file reader to the workspace, filters worker environment variables, validates worker responses, and enforces execution timeouts. The calculator interprets a restricted arithmetic AST and never evaluates arbitrary Python code.

A subprocess and filtered environment are **not a complete OS sandbox** against intentionally malicious third-party Python code. For untrusted plugins, use OS/container isolation with restricted filesystem mounts, network disabled by default, and resource limits. The included implementation is a best-effort isolation boundary, not a substitute for OS-level enforcement.
