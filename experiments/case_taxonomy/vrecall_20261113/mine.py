"""Mechanical selection of vertical-type fixes (vrecall criteria 二). WSL, read-only on /root/repos/linux.

    python3 mine.py      -> candidates.json, sample.json
"""
import gzip
import json
import random
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
REPO = "/root/repos/linux"
SCOPE = ["kernel/", "mm/", "lib/", "init/"] + [f"drivers/{d}/" for d in
                                               ("irqchip", "perf", "acpi", "clocksource", "iommu", "cpuidle", "firmware")]
NOT_IF = re.compile(r"^([A-Z0-9_]+|assert|panic|static_assert|WARN\w*|BUG\w*)$")
KEYW = {"if", "while", "for", "switch", "return", "sizeof", "else", "do", "case", "defined", "typeof", "__typeof__"}
CONST_ASSIGN = re.compile(r"^-\s*([A-Za-z_]\w*)\s*=\s*(true|false|0|1)\s*;\s*$")
CALL = re.compile(r"\b([A-Za-z_]\w*)\s*\(")


def main():
    scan = json.load(gzip.open("/root/work/effdep6/scan_CUR.json.gz", "rt"))
    ifaces = {n for n, d in scan["defs"].items() if any(a != "generic" for a in d) and not NOT_IF.match(n) and n not in KEYW}
    known = set(scan["defs"])
    paths = [p + "*.c" for p in SCOPE]
    cmd = ["git", "-C", REPO, "log", "v5.10..HEAD", "--no-merges", "--grep=^Fixes:", "-U8", "-p",
           "--format=COMMIT %H %s", "--"] + paths
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, errors="replace")
    cands, n_commits = [], 0
    cur = None
    fname, window, hunk_added = None, [], []

    def flush_hunk():
        pass
    for line in proc.stdout:
        line = line.rstrip("\n")
        if line.startswith("COMMIT "):
            n_commits += 1
            h, _, subj = line[7:].partition(" ")
            cur = {"commit": h, "subject": subj}
            fname, window = None, []
            continue
        if line.startswith("+++ "):
            fname = line[6:] if line.startswith("+++ b/") else None
            window = []
            continue
        if line.startswith("--- ") or line.startswith("diff --git") or line.startswith("index "):
            continue
        if line.startswith("@@"):
            window = []
            continue
        if not fname or not fname.endswith(".c") or not fname.startswith(tuple(SCOPE)) or cur is None:
            continue
        if line.startswith((" ", "-")):
            m = CONST_ASSIGN.match(line)
            if m:
                v, const = m.group(1), m.group(2)
                names = {n for w in window[-8:] for n in CALL.findall(w[1:]) if n != v and n not in KEYW and not NOT_IF.match(n)}
                hits = sorted(n for n in names if n in ifaces)
                unknown = sorted(n for n in names if n not in known)  # amendment 1: renamed / removed since
                if hits or unknown:
                    cands.append({**cur, "file": fname, "flag": v, "const": const, "interfaces": hits,
                                  "unknown": unknown, "line": line.strip()})
            window.append(line)
        elif line.startswith("+"):
            if cands and cands[-1]["commit"] == cur["commit"] and cands[-1]["file"] == fname:
                c = cands[-1]
                names = set(CALL.findall(line[1:]))
                if names & set(c["interfaces"]) and (re.search(rf"\b{re.escape(c['flag'])}\s*=", line) or re.search(r"\bif\s*\(", line)):
                    c["uses_return_value"] = True
    proc.wait()
    # amendment 1: a name unknown to the current scan counts if arch/ defines it at the fix's parent
    cache = {}

    def arch_defined(commit, name):
        k = (commit, name)
        if k not in cache:
            pat = rf"^[A-Za-z_].*\b{name}\s*\(|^\s*#\s*define\s+{name}\b"
            r = subprocess.run(["git", "-C", REPO, "grep", "-l", "-E", pat, f"{commit}^", "--", "arch/"],
                               capture_output=True, text=True)
            cache[k] = bool(r.stdout.strip())
        return cache[k]
    for c in cands:
        extra = [n for n in c.pop("unknown") if arch_defined(c["commit"], n)]
        c["renamed_interfaces"] = extra
        c["interfaces"] = sorted(set(c["interfaces"]) | set(extra))
    cands = [c for c in cands if c["interfaces"]]
    for c in cands:
        c.setdefault("uses_return_value", False)
    # one entry per commit (keep all matches)
    by = {}
    for c in cands:
        e = by.setdefault(c["commit"], {"commit": c["commit"], "subject": c["subject"], "matches": [], "uses_return_value": False})
        e["matches"].append({k: c[k] for k in ("file", "flag", "const", "interfaces", "renamed_interfaces", "line")})
        e["uses_return_value"] |= bool(c.get("uses_return_value"))
    commits = sorted(by.values(), key=lambda e: e["commit"])
    x1 = [e for e in commits if e["commit"].startswith("5bebe8de1926")]
    dev = set()
    sm = json.loads((CT / "boundary_closure_20261108/sample_match_v2.json").read_text(encoding="utf-8"))["samples"]
    dev |= {s["commit"][:12] for s in sm}
    dev |= {"5bebe8de1926", "9fd154ba926b"}
    pool = [e for e in commits if e["commit"][:12] not in dev]
    pick = pool if len(pool) <= 12 else random.Random(20261113).sample(pool, 12)
    (HERE / "candidates.json").write_text(json.dumps({"scanned_commits": n_commits, "interfaces": len(ifaces),
                                                      "selected": len(commits), "x1_selected": bool(x1),
                                                      "pool_after_dev_exclusion": len(pool), "commits": commits},
                                                     indent=1, ensure_ascii=False))
    (HERE / "sample.json").write_text(json.dumps(pick, indent=1, ensure_ascii=False))
    print("scanned", n_commits, "selected", len(commits), "x1", bool(x1), "pool", len(pool),
          "with_return_value_fix", sum(e["uses_return_value"] for e in commits))
    for e in pick:
        print(e["commit"][:12], e["subject"][:80], [(m["file"], m["flag"], m["interfaces"][:2]) for m in e["matches"][:2]])


if __name__ == "__main__":
    main()
