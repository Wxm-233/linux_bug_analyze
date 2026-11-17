source /mnt/d/homework/software/linux_bug_analyze/linux_bug_analyze/tools/wsl_env.sh
set -eu
python3 - "$@" <<'PY'
import base64
import subprocess
import sys

rev = "df2908090cda"
base = ["git", "-C", "/root/repos/linux"]
mode, *args = sys.argv[1:]
if mode == "show":
    path, *ranges = args
    data = subprocess.check_output(base + ["show", rev + ":" + path], text=True)
    lines = data.splitlines()
    print(f"=== {rev}:{path} ===")
    for span in ranges or [f"1:{len(lines)}"]:
        first, last = map(int, span.split(":"))
        for i in range(first, min(last, len(lines)) + 1):
            print(f"{i:5d} {lines[i-1]}")
elif mode in ("grep", "grep64"):
    pattern, *paths = args
    if mode == "grep64":
        pattern = base64.b64decode(pattern).decode()
    result = subprocess.run(base + ["grep", "-n", "-E", "-e", pattern, rev, "--"] + paths, text=True, capture_output=True)
    print(f"=== grep {pattern!r}; paths={paths!r}; status={result.returncode} ===")
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    if result.returncode not in (0, 1):
        raise SystemExit(result.returncode)
else:
    raise SystemExit("mode must be show or grep")
PY
