from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "verification.json"


def main() -> int:
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"], cwd=ROOT,
        capture_output=True, text=True,
    )
    output = (completed.stdout + "\n" + completed.stderr).strip()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "project": "Plugins & Extensibility",
        "test_command": "python -m pytest -q",
        "exit_code": completed.returncode,
        "passed": completed.returncode == 0,
        "output": output,
        "checks": ["manifest discovery", "tool schemas", "hot reload",
                   "Pydantic/JSON Schema validation", "path traversal defense",
                   "safe calculator", "explicit permissions", "timeout termination"],
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(output)
    print("\nVerification:", "PASS" if report["passed"] else "FAIL")
    print("Report:", REPORT)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
