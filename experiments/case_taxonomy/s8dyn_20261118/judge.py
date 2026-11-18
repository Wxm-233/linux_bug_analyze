"""s8dyn criteria 四/五: judge runs/<tag>/*.log -> judge_<tag>.json / .txt"""
import json, re, sys
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
tag = sys.argv[1]
PRED = {"A": True, "B": False, "C": False, "D": False, "E": False}
rows = []
for p in sorted((HERE / "runs" / tag).glob("*.log")):
    cell, run = p.stem.split(".run")
    L = p.read_text(errors="replace").split("\n")
    end = any(l.startswith("@@END") for l in L) or (any("reboot: Power down" in l for l in L) and sum(l.startswith("@@WORKER") for l in L) >= 3)  # amendment 1
    hit, other = False, []
    for i, l in enumerate(L):
        if "WARNING:" in l and "kernel/smp.c" in l:
            if any("__kernel_map_pages" in x for x in L[i:i + 40]):
                hit = True
        if ("WARNING:" in l or "BUG:" in l) and "kernel/smp.c" not in l:
            other.append(l.strip()[:160])
    cpus = next((l.split()[1] for l in L if l.startswith("@@CPUS")), "?")
    rows.append({"cell": cell, "run": int(run), "end": end, "hit": hit, "cpus": cpus, "other": other[:3],
                 "valid": end or hit, "hang": not end and not hit})
by = defaultdict(list)
for r in rows:
    by[r["cell"]].append(r)
out, ok_all = [], True
for c in sorted(by):
    rs = by[c]
    n_hit = sum(r["hit"] for r in rs)
    n_valid = sum(r["valid"] for r in rs)
    match = (n_hit == len(rs)) if PRED[c] else (n_hit == 0)
    ok_all &= match and n_valid == len(rs)
    out.append(f"{c}: hit {n_hit}/{len(rs)} valid {n_valid}/{len(rs)} cpus {[r['cpus'] for r in rs]} pred {'hit' if PRED[c] else 'none'} -> {'OK' if match else 'MISMATCH'}"
               + (f" other={rs[0]['other']}" if rs[0]['other'] else "") + (f" hang={sum(r['hang'] for r in rs)}" if any(r['hang'] for r in rs) else ""))
out.append(f"ALL PREDICTIONS {'MATCH' if ok_all else 'DO NOT ALL MATCH'}")
(HERE / f"judge_{tag}.json").write_text(json.dumps({"rows": rows, "all_match": ok_all}, indent=1))
(HERE / f"judge_{tag}.txt").write_text("\n".join(out) + "\n")
print("\n".join(out))
