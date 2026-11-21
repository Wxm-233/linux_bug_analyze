"""heldout2 criteria 四 + amendment 1: build the analysis and sealed evaluation sets from adjudication.json.
Same logic as heldout_commit_20261117/heldout_run.py build(); additionally excludes the previous held-out set, keeps the two
sets' negatives disjoint (sealed first), and marks a positive "used" when any of its fixes is in taint.json. WSL.

    python3 build2.py     -> set_sealed.json, set_analysis.json, build.log
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "commitmode_20261117"))
import commitmode as M  # noqa: E402
import dataset as DSET  # noqa: E402

git = DSET.git
ROOT = M.git("rev-list", "--max-parents=0", "HEAD").split()[-1].strip()


def main():
    adj = json.loads((HERE / "adjudication.json").read_text(encoding="utf-8"))
    taint = json.loads((HERE / "taint.json").read_text())
    dev = json.loads((CT / "commitmode_20261117/dataset.json").read_text())
    old = json.loads((CT / "heldout_commit_20261117/heldout_set.json").read_text())
    seen_pos = {p["commit"] for p in dev["positives"] + old["positives"]}
    seen_neg = {n["commit"] for n in dev["negatives"] + old["negatives"]}
    targets = DSET.fix_targets()
    taken_neg = set()
    log = []
    for name in ("sealed", "analysis"):
        pos = {}
        for r in adj[name]:
            if r["final"] != "是":
                continue
            fix = M.full(r["commit"])
            msg = git("log", "-1", "--format=%B", fix)
            for t in re.findall(r"^\s*Fixes:\s*([0-9a-fA-F]{8,40})", msg, re.M):
                h = M.full(t)
                if not h or h == ROOT or h in seen_pos:
                    continue
                p = pos.setdefault(h, {"commit": h, "short": h[:12], "info": git("log", "-1", "--format=%h|%cs|%s", h).strip(),
                                       "fixes": [], "categories": set(), "fix_funcs": set(), "used": False})
                p["fixes"].append(fix[:12])
                p["categories"].add(r["category"] or "OTHER")
                p["fix_funcs"].update(map(tuple, DSET.touched_funcs(fix)))
                p["used"] = p["used"] or fix[:12] in taint[name]
        posset = {h[:8] for h in pos}
        negs = {}
        for h, p in sorted(pos.items(), key=lambda kv: kv[1]["info"]):
            fs = [f for f in DSET.files_of(h) if DSET.scanned(f)]
            p["files"] = fs
            p["neg"] = []
            if not fs:
                continue
            ct = int(git("log", "-1", "--format=%ct", h).strip())
            lines = git("log", "--no-merges", "--format=%H %ct", f"--since={ct - 365 * 86400}", f"--until={ct + 365 * 86400}", "HEAD", "--", *fs)
            cands = []
            for ln in lines.split("\n"):
                if not ln:
                    continue
                c, t = ln.split()
                if c == h or c[:8] in targets or c[:8] in posset or c in negs or c in seen_pos or c in seen_neg or c in taken_neg:
                    continue
                cands.append((int(t) - ct, c))
            for x in (max((x for x in cands if x[0] < 0), default=None), min((x for x in cands if x[0] > 0), default=None)):
                if x:
                    negs[x[1]] = {"commit": x[1], "short": x[1][:12], "for": h[:12], "dt_days": round(x[0] / 86400, 1),
                                  "info": git("log", "-1", "--format=%h|%cs|%s", x[1]).strip()}
                    p["neg"].append(x[1][:12])
        taken_neg |= set(negs)
        out = {"positives": [dict(p, categories=sorted(p["categories"]), fix_funcs=sorted(p["fix_funcs"])) for p in pos.values()],
               "negatives": list(negs.values())}
        (HERE / f"set_{name}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        P = out["positives"]
        line = (f"{name}: positives {len(P)} (used before {sum(p['used'] for p in P)}, clean {sum(not p['used'] for p in P)}), "
                f"positives without scanned files {sum(not p['files'] for p in P)}, negatives {len(out['negatives'])}")
        print(line)
        log.append(line)
    (HERE / "build.log").write_text("\n".join(log) + "\n")


if __name__ == "__main__":
    main()
