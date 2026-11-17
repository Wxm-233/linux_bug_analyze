"""Compare differential-test runs (criteria sections 3-4).

    python3 compare.py runs/<tag> [kernel name ...]   -> runs/<tag>/compare.json

Each log runs/<tag>/<name>.run<i>.log holds JSON lines between @@DT BEGIN and @@DT END. Kernels are checked for
stability over their runs; stable test keys are then compared across kernels.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


def parse(log):
    text = Path(log).read_text(errors="replace")
    m = re.search(r"@@DT BEGIN\n(.*?)@@DT END", text, re.S)
    if not m:
        return None
    out = {}
    for line in m.group(1).splitlines():
        line = line.strip().replace("\r", "")
        if not line.startswith("{"):
            continue
        d = json.loads(line)
        key = d["test"] + ("/" + d["case"] if "case" in d else "")
        out[key] = d["result"]
    return out


def main():
    run = Path(sys.argv[1])
    names = sys.argv[2:] or sorted({p.name.split(".run")[0] for p in run.glob("*.run*.log")})
    per, stable, unstable, missing = {}, {}, defaultdict(list), []
    for n in names:
        runs = [parse(p) for p in sorted(run.glob(f"{n}.run*.log"))]
        if not runs or any(r is None for r in runs):
            missing.append(n)
            continue
        per[n] = runs
        keys = set().union(*runs)
        stable[n] = {}
        for k in sorted(keys):
            vals = {r.get(k) for r in runs}
            if len(vals) == 1:
                stable[n][k] = vals.pop()
            else:
                unstable[n].append({k: sorted(map(str, vals))})
    keys = sorted(set().union(*[set(v) for v in stable.values()])) if stable else []
    table = {k: {n: stable[n].get(k) for n in stable} for k in keys}
    diffs = {k: v for k, v in table.items() if len({x for x in v.values()}) > 1}
    out = {"kernels": list(stable), "runs_per_kernel": {n: len(r) for n, r in per.items()}, "missing_or_unparsed": missing,
           "unstable": dict(unstable), "table": table, "differences": diffs}
    (run / "compare.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    w = max(len(k) for k in keys) if keys else 10
    print(" " * w, *[n[:14].ljust(14) for n in stable])
    for k in keys:
        print(k.ljust(w), *[str(table[k][n])[:14].ljust(14) for n in stable], "  <diff" if k in diffs else "")
    print("unstable:", dict(unstable), "| missing:", missing)


if __name__ == "__main__":
    main()
