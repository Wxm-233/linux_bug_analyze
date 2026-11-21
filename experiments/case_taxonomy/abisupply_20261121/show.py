"""criteria 六: design-side sample (Random(20261121), 60 + known move_pages fix); print message + compat-related hunks. WSL.

    python3 show.py sample          -> design_sample.json
    python3 show.py show <from> <to> -> print items [from, to)
"""
import json
import random
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = "/root/repos/linux"
KNOWN = "229e2253766c"
TRAILER = re.compile(r"^\s*(Signed-off-by|Cc|Reviewed-by|Acked-by|Tested-by|Link|Suggested-by|Co-developed-by|Closes|Message-ID|"
                     r"Reported-and-tested-by|Debugged-by)\s*:", re.I)


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace").stdout


def sample():
    d = json.loads((HERE / "design.json").read_text())
    rest = sorted((c for c in d if c["commit"] != KNOWN), key=lambda c: c["commit"])
    pick = random.Random(20261121).sample(rest, 60) if len(rest) > 60 else rest
    pick = sorted(pick, key=lambda c: c["date"]) + [c for c in d if c["commit"] == KNOWN]
    (HERE / "design_sample.json").write_text(json.dumps(pick, indent=1, ensure_ascii=False))
    print("design", len(d), "sample", len(pick))


def show(a, b):
    pick = json.loads((HERE / "design_sample.json").read_text())
    for i, c in enumerate(pick[a:b], a):
        body = git("log", "-1", "--format=%B", c["commit"]).split("\n")
        msg = [ln for ln in body if ln.strip() and not TRAILER.match(ln)][:9]
        print(f"=== [{i}] {c['commit']} {c['date']} fixes={c['fixes']} files={c['files'][:4]}")
        print("\n".join("  " + ln[:150] for ln in msg))
        patch = git("show", "--format=", "--no-color", "-U2", c["commit"], "--", ".", ":(exclude)Documentation", ":(exclude)tools")
        out = [ln for ln in patch.split("\n") if ln.startswith(("@@", "+", "-")) and not ln.startswith(("+++", "---"))]
        print("\n".join("  | " + ln[:140] for ln in out[:18]))


if __name__ == "__main__":
    if sys.argv[1] == "sample":
        sample()
    else:
        show(int(sys.argv[2]), int(sys.argv[3]))
