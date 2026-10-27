"""Capture the final boundary suite and development replay exactly once."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    receipt = HERE / "execution_receipt.json"
    if receipt.exists() or (HERE / "results.json").exists():
        raise SystemExit("Preserve existing output before a new development run")
    code = [HERE / n for n in ("interface_fact_extractor.py", "run_development.py", "run_checks.py", "test_interface_facts.py")]
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in code}
    rows = []
    commands = [
        ("tests", [sys.executable, "-B", "-X", "utf8", "-m", "unittest", "discover", "-s", str(HERE), "-p", "test_interface_facts.py", "-v"]),
        ("development", [sys.executable, "-B", "-X", "utf8", str(HERE / "run_development.py")]),
    ]
    for name, argv in commands:
        begin = datetime.now(timezone.utc).isoformat()
        result = subprocess.run(argv, capture_output=True)
        for stream in ("stdout", "stderr"):
            destination = HERE / (name + "_" + stream + ".txt")
            if destination.exists():
                raise SystemExit("refuse log overwrite")
            destination.write_bytes(getattr(result, stream))
        rows.append(dict(name=name, argv=argv, returncode=result.returncode,
                         started_at_utc=begin, ended_at_utc=datetime.now(timezone.utc).isoformat()))
        if result.returncode:
            break
    unchanged = before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in code}
    receipt.write_text(json.dumps(dict(commands=rows, code_sha256=before, code_unchanged=unchanged,
                                      development_only=True), indent=2) + "\n", encoding="utf-8")
    if not unchanged or len(rows) != 2 or any(r["returncode"] for r in rows):
        raise SystemExit("development failed; outputs preserved")
    print("Boundary suite and eight-revision development replay completed; see execution_receipt.json")


if __name__ == "__main__":
    main()
