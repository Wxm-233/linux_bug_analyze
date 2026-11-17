"""commitmode criteria 二: development set. WSL.
    python3 dataset.py   -> dataset.json, fixes_targets.txt (prefix set of every Fixes: tag in HEAD history)

positives: introducing commits named by Fixes: tags of the historical fix samples (fixes_raw.json)
negatives: per positive P, the nearest non-merge commit before and the nearest after P (committer time) that touches a
           scanned .c/.h file P touched, is not named by any Fixes: tag in HEAD history, is not a positive, and is within 365 days.
"""
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "p1check_20261115"))
import p1check as C  # noqa: E402

KSRC = "/root/repos/linux"
ROOT = "1da177e4c3f41524e886b7f1b8a0c1fc7321cac2"


def git(*a):
    return subprocess.run(["git", "-C", KSRC, *a], capture_output=True, text=True).stdout


def scanned(p):
    """union of the four engines' scopes (criteria 二.3)"""
    if p.endswith(".c") and (p.startswith(("mm/", "kernel/", "lib/", "fs/")) or re.match(r"arch/[^/]+/(kernel|mm)/", p)):
        return True
    return p.endswith(".h") and p.startswith(("include/linux/", "mm/", "fs/"))


def files_of(c):
    return [p for p in git("show", "--format=", "--name-only", "-m", "--first-parent", c).split("\n") if p]


def fix_targets():
    out = set()
    proc = subprocess.Popen(["git", "-C", KSRC, "log", "--format=%B", "HEAD"], stdout=subprocess.PIPE, text=True, errors="replace")
    pat = re.compile(r"^\s*Fixes:\s*([0-9a-fA-F]{8,40})", re.I)
    for ln in proc.stdout:
        m = pat.match(ln)
        if m:
            out.add(m.group(1).lower()[:8])
    proc.wait()
    return out


def touched_funcs(commit):
    """(file, func) of functions overlapping the commit's hunks, on the parent side and on the commit side"""
    out = set()
    diff = git("show", "--format=", "-U0", "--first-parent", "-m", commit)
    hunks = defaultdict(lambda: {"a": [], "b": []})
    cur_a = cur_b = None
    for ln in diff.split("\n"):
        if ln.startswith("--- "):
            cur_a = ln[6:] if ln.startswith("--- a/") else None
        elif ln.startswith("+++ "):
            cur_b = ln[6:] if ln.startswith("+++ b/") else None
        elif ln.startswith("@@"):
            m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))?", ln)
            a, n, b, k = int(m.group(1)), int(m.group(2) or 1), int(m.group(3)), int(m.group(4) or 1)
            if cur_a:
                hunks[("a", cur_a)]["a"].append((a, a + max(n, 1) - 1))
            if cur_b:
                hunks[("b", cur_b)]["b"].append((b, b + max(k, 1) - 1))
    for (side, path), hs in hunks.items():
        if not path.endswith((".c", ".h")):
            continue
        rev = f"{commit}^" if side == "a" else commit
        src = git("show", f"{rev}:{path}")
        try:
            t = C.tokenize(C.strip(src))
            fns = [(name, t[b0][1] - 3, t[b1][1]) for name, params, b0, b1 in C.functions(t)]
        except (IndexError, RecursionError):
            continue
        for lo, hi in hs[side]:
            for name, f0, f1 in fns:
                if f0 <= hi and f1 >= lo:
                    out.add((path, name))
    return sorted(out)


def main():
    raw = json.loads((HERE / "fixes_raw.json").read_text())
    targets = fix_targets()
    (HERE / "fixes_targets_count.txt").write_text(str(len(targets)) + "\n")
    pos = {}
    for r in raw:
        for t in r["fixes"]:
            h = t["resolved"]
            if not h or h == ROOT:
                continue
            p = pos.setdefault(h, {"commit": h, "short": h[:12], "info": t["info"], "lines": set(), "fixes": [], "fix_funcs": set()})
            p["lines"].add(r["line"])
            p["fixes"].append(r["fix"])
            p["fix_funcs"].update(map(tuple, touched_funcs(r["fix"])))
    posset = {h[:8] for h in pos}
    negs = {}
    for h, p in sorted(pos.items(), key=lambda kv: kv[1]["info"]):
        fs = [f for f in files_of(h) if scanned(f)]
        p["files"] = fs
        if not fs:
            p["neg"] = []
            continue
        ct = int(git("log", "-1", "--format=%ct", h).strip())
        lines = git("log", "--no-merges", "--format=%H %ct", f"--since={ct - 365 * 86400}", f"--until={ct + 365 * 86400}", "HEAD", "--", *fs)
        cands = []
        for ln in lines.split("\n"):
            if not ln:
                continue
            c, t = ln.split()
            if c == h or c[:8] in targets or c[:8] in posset or c in negs:
                continue
            cands.append((int(t) - ct, c))
        before = max((x for x in cands if x[0] < 0), default=None)
        after = min((x for x in cands if x[0] > 0), default=None)
        p["neg"] = []
        for x in (before, after):
            if x:
                negs[x[1]] = {"commit": x[1], "short": x[1][:12], "for": h[:12], "dt_days": round(x[0] / 86400, 1),
                              "info": git("log", "-1", "--format=%h|%cs|%s", x[1]).strip()}
                p["neg"].append(x[1][:12])
    out = {"positives": [dict(p, lines=sorted(p["lines"]), fix_funcs=sorted(p["fix_funcs"])) for p in pos.values()],
           "negatives": list(negs.values()), "fixes_targets": len(targets)}
    (HERE / "dataset.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print("positives", len(out["positives"]), "negatives", len(out["negatives"]), "Fixes targets", len(targets))
    for p in out["positives"]:
        print(" P", p["info"][:70], "|", ",".join(p["lines"]), "| files", len(p["files"]), "| fix funcs", len(p["fix_funcs"]), "| neg", p["neg"])
    for n in out["negatives"]:
        print(" N", n["info"][:80], "| for", n["for"], n["dt_days"])


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    main()
