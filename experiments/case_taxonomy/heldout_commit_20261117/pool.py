"""heldout_commit criteria 二: pool, sample of 60, export for blind labelling. WSL, read-only.
    python3 pool.py   -> pool.json, sample.json, show_heldout.txt
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
import show as DS  # noqa: E402  (read-only import: hunks(), TRAILER, git())

REPO = "/root/repos/linux"


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True, errors="replace").stdout


def full(c):
    return git("rev-parse", "--verify", "-q", c + "^{commit}").strip()


cand = json.loads((CT / "depmine_20261115/candidates.json").read_text(encoding="utf-8"))
dsamp = json.loads((CT / "depmine_20261115/sample.json").read_text(encoding="utf-8"))
sampled = {h for f in "ABC" for h in dsamp[f]}
dev_fixes = {full(r["fix"]) for r in json.loads((CT / "commitmode_20261117/fixes_raw.json").read_text())}
dev = json.loads((CT / "commitmode_20261117/dataset.json").read_text())
dev_pos = {p["commit"] for p in dev["positives"]}

pool, excluded = [], {"depmine_sampled": 0, "dev_fix": 0, "fixes_dev_positive": 0}
for c in cand["commits"]:
    h = c["commit"]
    if h in sampled:
        excluded["depmine_sampled"] += 1
        continue
    if full(h) in dev_fixes:
        excluded["dev_fix"] += 1
        continue
    msg = git("log", "-1", "--format=%B", h)
    tags = [full(t) for t in re.findall(r"^\s*Fixes:\s*([0-9a-fA-F]{8,40})", msg, re.M)]
    if any(t in dev_pos for t in tags if t):
        excluded["fixes_dev_positive"] += 1
        continue
    pool.append(h)
rng = random.Random(20261117)
pick = rng.sample(pool, min(60, len(pool)))
rng.shuffle(pick)
(HERE / "pool.json").write_text(json.dumps({"total_candidates": len(cand["commits"]), "excluded": excluded, "pool": pool}, indent=1))

byc = {c["commit"]: c for c in cand["commits"]}
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
(HERE / "sample.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
(HERE / "show_heldout.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
print("candidates", len(cand["commits"]), "excluded", excluded, "pool", len(pool), "sample", len(pick))
