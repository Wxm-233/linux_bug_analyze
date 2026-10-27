"""Capture the single frozen offline execution; never run kernel workflows."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
assert not (HERE / "first_run.receipt.json").exists(), "no repeated first execution"
pre = json.loads((HERE / "execution_pre.json").read_text(encoding="utf-8"))
for path, expected in pre["files"].items():
    assert hashlib.sha256((HERE / path).read_bytes()).hexdigest() == expected, path
argv = [sys.executable, "-B", "-X", "utf8", str(HERE / "run_override.py")]
exception = None
try:
    result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
    stdout, stderr, rc = result.stdout, result.stderr, result.returncode
except subprocess.TimeoutExpired as e:
    stdout, stderr, rc, exception = e.stdout or b"", e.stderr or b"", "timeout", repr(e)
except OSError as e:
    stdout, stderr, rc, exception = b"", b"", "os_error", repr(e)
for stream, content in [("stdout", stdout), ("stderr", stderr)]:
    (HERE / ("first_run." + stream + ".bin")).write_bytes(content)
receipt = {"argv": argv, "returncode": rc, "stdout_bytes": len(stdout),
           "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
           "stderr_sha256": hashlib.sha256(stderr).hexdigest(), "exception": exception,
           "offline_runner_executions": 1, "kernel_or_QEMU_executions": 0}
(HERE / "first_run.receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
assert rc == 0, receipt
print(json.dumps(receipt, ensure_ascii=False))
