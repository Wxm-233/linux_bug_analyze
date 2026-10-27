"""Persist stdout/stderr of the single offline first execution."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
assert not (HERE / "first_run.receipt.json").exists(), "no repeated first execution"
freeze = json.loads((HERE / "execution_pre.json").read_text(encoding="utf-8"))
for path, expected in freeze["files"].items():
    assert hashlib.sha256((HERE / path).read_bytes()).hexdigest() == expected, path
argv = [sys.executable, "-B", "-X", "utf8", str(HERE / "run_offline.py")]
exception = None
try:
    r = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
    stdout, stderr, returncode = r.stdout, r.stderr, r.returncode
except subprocess.TimeoutExpired as e:
    stdout, stderr, returncode = e.stdout or b"", e.stderr or b"", "timeout"
    exception = repr(e)
except OSError as e:
    stdout, stderr, returncode = b"", b"", "os_error"
    exception = repr(e)
for stream, content in [("stdout", stdout), ("stderr", stderr)]:
    (HERE / ("first_run." + stream + ".bin")).write_bytes(content)
receipt = {"argv": argv, "returncode": returncode, "stdout_bytes": len(stdout),
           "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
           "stderr_sha256": hashlib.sha256(stderr).hexdigest(), "exception": exception,
           "offline_runner_executions": 1, "kernel_or_QEMU_executions": 0}
(HERE / "first_run.receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
assert returncode == 0, receipt
print(json.dumps(receipt, ensure_ascii=False))
