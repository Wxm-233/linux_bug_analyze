"""s8dyn: per round x cell summary (WARN hits, completed runs, hangs, hangs whose stall stacks show __kernel_map_pages -> IPI wait)"""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
out = []
for tag in ("main", "aia2", "st"):
    for p in sorted((HERE / "runs" / tag).glob("*.log")):
        cell, run = p.stem.split(".run")
        if tag != "main" and cell in "DE":
            continue
        L = p.read_text(errors="replace").split("\n")
        warn = any("WARNING:" in l and "kernel/smp.c" in l and any("__kernel_map_pages" in x for x in L[i:i + 40]) for i, l in enumerate(L))
        end = any("@@END" in l for l in L) or (any("reboot: Power down" in l for l in L) and sum(l.startswith("@@WORKER") for l in L) >= 3)
        stall = sum("rcu_sched detected stalls" in l for l in L)
        ipi_wait = any("smp_call_function_many_cond" in l and any("__kernel_map_pages" in x for x in L[i:i + 8]) for i, l in enumerate(L)
                       if not any("WARNING:" in y for y in L[max(0, i - 25):i]))
        out.append({"round": tag, "cell": cell, "run": int(run), "warn_hit": warn, "completed": end, "stalls": stall,
                    "stall_in_kmp_ipi_wait": (not end) and ipi_wait})
(HERE / "summary.json").write_text(json.dumps(out, indent=1))
from collections import defaultdict
agg = defaultdict(lambda: [0, 0, 0, 0, 0])
for r in out:
    a = agg[(r["round"], r["cell"])]
    a[0] += 1; a[1] += r["warn_hit"]; a[2] += r["completed"]; a[3] += (not r["completed"]); a[4] += r["stall_in_kmp_ipi_wait"]
print("round cell runs warn_hit completed hung hung_in_kmp_ipi_wait")
for k in sorted(agg):
    print(k[0], k[1], *agg[k])
