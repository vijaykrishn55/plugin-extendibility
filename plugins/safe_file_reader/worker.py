import json
import sys
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field


class ReadArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file_path: str = Field(min_length=1, max_length=240)


def handle(request: dict) -> dict:
    request_id = request.get("id", 1)
    try:
        params = request["params"]
        args = ReadArgs.model_validate(params["arguments"])
        root = Path(params["workspace"]).resolve()
        candidate = Path(args.file_path)
        if candidate.is_absolute():
            raise PermissionError("Absolute paths are not allowed")
        target = (root / candidate).resolve()
        if not target.is_relative_to(root):
            raise PermissionError("Access denied: path escapes workspace")
        if not target.is_file():
            raise FileNotFoundError("Workspace file does not exist")
        if target.stat().st_size > 256_000:
            raise ValueError("File exceeds 256 KB read limit")
        content = target.read_text(encoding="utf-8")
        result = {"content": content, "path": args.file_path,
                  "bytes": len(content.encode("utf-8"))}
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except Exception as exc:
        return {"jsonrpc": "2.0", "id": request_id,
                "error": {"code": -32003, "message": str(exc)}}


def main() -> None:
    try:
        request = json.loads(sys.stdin.readline())
        response = handle(request)
    except Exception as exc:
        response = {"jsonrpc": "2.0", "id": 1,
                    "error": {"code": -32600, "message": str(exc)}}
    print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
