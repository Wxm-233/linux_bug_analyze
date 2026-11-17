"""Foreground batch with retained console output and elapsed time."""
import json
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
started = time.monotonic()
stamp = datetime.now(timezone.utc).isoformat()
logdir = HERE / "execution"
logdir.mkdir(exist_ok=True)
log = logdir / (datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + "_".join(sys.argv[1:3]) + ".log")
with log.open("w", encoding="utf-8") as stream:
    program, arguments = ("merge_staged.py", sys.argv[2:]) if sys.argv[1] == "merge-staged" else ("enumerate.py", sys.argv[1:])
    process = subprocess.Popen([sys.executable, "-B", str(HERE / program), *arguments],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        stream.write(line)
        stream.flush()
        print(line, end="", flush=True)
    code = process.wait()
with (logdir / "timings.jsonl").open("a", encoding="utf-8") as stream:
    stream.write(json.dumps({"start_utc": stamp, "args": sys.argv[1:], "elapsed_seconds": round(time.monotonic()-started, 3),
                             "exit_code": code, "log": log.name}) + "\n")
sys.exit(code)
