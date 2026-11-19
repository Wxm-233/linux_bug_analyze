"""weakov2 criteria 三.1: mine independent samples (no analyzer involved).
Fix commits (Fixes: tag, no merges) in v5.10..HEAD whose diff changes an arch/*/*.c function that has the same name as
a __weak function in common code (names collected at v5.10, v6.1, v6.6, v6.12 and HEAD).

    python3 mine.py names        -> weak_names.json
    python3 mine.py commits      -> mined.json (all such fix commits, with the touched override functions and diff stats)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "weakov_20261118"))
import weakov as W  # noqa: E402

C = W.C
HEAD = "df2908090cda"
TAGS = ["v5.10", "v6.1", "v6.6", "v6.12", HEAD]


def weak_names(rev):
    files = [ln.split(":", 1)[1] for ln in C.git("grep", "-l", "-w", "__weak", rev, "--", "*.c", ":(exclude)arch").split("\n") if ln]
    out = set()
    for p, s in C.cat_files(rev, files).items():
        for name, hd, w, st, t, b0, b1 in W.defs_in(s):
            if w and not st:
                out.add(name)
    return out


def cmd_names():
    allv = {}
    for r in TAGS:
        n = weak_names(r)
        allv[r] = sorted(n)
        print(r, len(n))
    union = sorted(set().union(*map(set, allv.values())))
    (HERE / "weak_names.json").write_text(json.dumps({"per_tag": allv, "union": union}, indent=1))
    print("union", len(union))


FUNC_HDR = re.compile(r"^@@ [^@]* @@\s*(.*)$")


def touched_funcs(c, names):
    """{(path, func)} for arch/*.c hunks whose context or changed lines name a weak function definition"""
    diff = C.git("show", "--format=", "-U0", "--function-context", c, "--", "arch/*.c")
    out, path = set(), None
    cur = None
    for ln in diff.split("\n"):
        if ln.startswith("+++ "):
            path = ln[6:] if ln.startswith("+++ b/") else None
            continue
        if path is None:
            continue
        m = FUNC_HDR.match(ln)
        if m:
            cur = None
            continue
        if ln[:1] in (" ", "+", "-"):
            mm = re.match(r"^[ +-](?:[A-Za-z_][\w\s\*]*?\s+\**)?([A-Za-z_]\w*)\s*\([^;]*$", ln)
            if mm and not ln[1:2].isspace() and mm.group(1) in names:
                cur = mm.group(1)
            if cur and ln[:1] in "+-":
                out.add((path, cur))
    return out


def cmd_commits():
    names = set(json.loads((HERE / "weak_names.json").read_text())["union"])
    revs = C.git("log", "--no-merges", "--format=%H", "--grep=^Fixes:", f"v5.10..{HEAD}", "--", "arch/*.c").split()
    print("fix commits touching arch/*.c:", len(revs), flush=True)
    rows = []
    for i, c in enumerate(revs):
        tf = touched_funcs(c, names)
        if tf:
            subj = C.git("log", "-1", "--format=%s", c).strip()
            body = C.git("log", "-1", "--format=%b", c)
            fixes = re.findall(r"^Fixes:\s*([0-9a-f]{8,40})", body, re.M)
            rows.append({"commit": c[:12], "subject": subj, "fixes": [f[:12] for f in fixes],
                         "funcs": sorted(f"{p}:{f}" for p, f in tf)})
        if i % 500 == 0:
            print(i, len(rows), flush=True)
    (HERE / "mined.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    print("mined", len(rows))


if __name__ == "__main__":
    {"names": cmd_names, "commits": cmd_commits}[sys.argv[1]]()
