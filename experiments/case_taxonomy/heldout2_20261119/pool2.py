"""heldout2 criteria 二: remaining 110 fixes of the previous pool, split 44 analysis / 66 sealed (Random(20261119)),
export each set for blind labelling in the same format as heldout_commit_20261117/pool.py. WSL, read-only.

    python3 pool2.py    -> split.json, sample_analysis.json, sample_sealed.json, show_analysis.txt, show_sealed.txt
"""
import json
import random
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "depmine_20261115"))
import show as DS  # noqa: E402  (read-only import: hunks(), TRAILER)

REPO = "/root/repos/linux"


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace").stdout


prev = CT / "heldout_commit_20261117"
pool = json.loads((prev / "pool.json").read_text())["pool"]
taken = {r["commit"] for r in json.loads((prev / "sample.json").read_text(encoding="utf-8"))}
rest = [h for h in pool if h not in taken]
assert len(rest) == 110, len(rest)
rng = random.Random(20261119)
order = rest[:]
rng.shuffle(order)
analysis, sealed = order[:44], order[44:]
(HERE / "split.json").write_text(json.dumps({"seed": 20261119, "analysis": analysis, "sealed": sealed}, indent=1))

cand = json.loads((CT / "depmine_20261115/candidates.json").read_text(encoding="utf-8"))
byc = {c["commit"]: c for c in cand["commits"]}


def export(name, commits, seed):
    pick = commits[:]
    random.Random(seed).shuffle(pick)
    L, rows = [], []
    for k, h in enumerate(pick, 1):
        c = byc[h]
        msg = git("log", "-1", "--format=%B", h)
        body = [x for x in msg.splitlines() if not DS.TRAILER.match(x)]
        body = [x for x in body if not re.match(r"^\s*Fixes:", x)]          # the introducing commit is not shown to annotators
        while body and not body[-1].strip():
            body.pop()
        files = sorted({m["file"] for f in c["forms"] for m in c["forms"][f]})
        needles = sorted({m["line"][:60] for f in c["forms"] for m in c["forms"][f]})
        L += ["=" * 100, f"[{k}] {h[:12]}  {c['subject']}", "-- message:"] + ["   " + x for x in body[:40]] + (["   …"] if len(body) > 40 else [])
        for f, hk in DS.hunks(h, files, [n.strip()[:40] for n in needles]):
            L.append(f"-- hunk {f}:")
            L += ["   " + x for x in hk[:45]] + (["   …"] if len(hk) > 45 else [])
        rows.append({"k": k, "commit": h, "subject": c["subject"], "forms": sorted(c["forms"])})
    (HERE / f"sample_{name}.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    (HERE / f"show_{name}.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(name, len(rows))


export("analysis", analysis, 1)
export("sealed", sealed, 2)
