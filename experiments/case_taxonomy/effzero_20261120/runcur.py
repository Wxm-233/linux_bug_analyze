"""Frozen run on the current version (criteria 四): effzero + config evidence, patchmatch, overlap with the 8-engine table. WSL.

    python3 runcur.py
"""
import csv
import json
import time
from pathlib import Path

import effzero as E
import patchmatch as PM

HERE = Path(__file__).resolve().parent
CT = HERE.parent
REV = "df2908090cda"
BUILDS = {a: f"/root/work/boundary_build/{a}_defconfig" for a in ("riscv", "arm64", "x86_64")}
SRC = "/root/repos/linux/"


def compiled_sets():  # same as buildattr_20261120/attr.py
    out = {}
    for a, d in BUILDS.items():
        cc = json.load(open(d + "/compile_commands.json"))
        out[a] = {e["file"][len(SRC):] for e in cc if e["file"].startswith(SRC) and e["file"].endswith(".c")}
    return out


def main():
    t0 = time.time()
    cs = compiled_sets()
    ez = E.run(REV, str(HERE / "cur/effzero.json"), compiled=cs)
    pm = PM.main(REV, str(HERE / "cur/patchmatch.json"))
    base = []
    with open(CT / "scan3_20261119/tables/df2908090cda.csv", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            base.append(row)
    keys = list(base[0].keys())
    print("baseline columns:", keys)
    fcol = next(k for k in keys if k in ("文件", "file"))
    gcol = next(k for k in keys if k in ("函数", "func"))
    pcol = next((k for k in keys if k in ("优先级", "priority")), None)
    bset = {(r[fcol], r[gcol]) for r in base}
    bset1 = {(r[fcol], r[gcol]) for r in base if pcol and r[pcol] in ("1", "一", "优先级一")}
    ezk = [(c["file"], c["func"]) for c in ez["cands"]]
    pmk = [(c["file"], c["func"]) for c in pm["cands"]]
    ez20, pm20 = set(ezk[:20]), set(pmk[:20])
    summ = {
        "effzero": {"n": len(ezk), "forms": ez["stats"]["forms"], "groups_reported": len({c["group"] for c in ez["cands"]}),
                    "with_config_evidence": sum(1 for c in ez["cands"] if any(c.get("compiled", {}).values())),
                    "arch_evidence": sum(1 for c in ez["cands"] if c["arch"]),
                    "overlap_baseline": len(set(ezk) & bset), "overlap_baseline_p1": len(set(ezk) & bset1),
                    "new_vs_baseline": len(set(ezk) - bset), "top20_overlap_baseline": len(ez20 & bset),
                    "secs": ez["stats"]["secs_total"], "maxrss_mb": ez["stats"]["maxrss_mb"]},
        "patchmatch": {"n": len(pmk), "by_pattern": pm["by_pattern"], "overlap_baseline": len(set(pmk) & bset),
                       "overlap_effzero": len(set(pmk) & set(ezk)), "top20_overlap_effzero": len(pm20 & ez20)},
        "baseline": {"n": len(base), "distinct_file_func": len(bset), "p1_file_func": len(bset1)},
        "secs": round(time.time() - t0),
    }
    (HERE / "cur/summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False))
    print(json.dumps(summ, indent=1, ensure_ascii=False))
    for c in ez["cands"][:40]:
        print(c["rank"], c["form"], c["file"], c["line"], c["func"], c.get("origin"), c["group"], c.get("n_zero"), c.get("n_nonzero"),
              "".join(a[0] for a, v in c.get("compiled", {}).items() if v))


if __name__ == "__main__":
    import sys
    sys.setrecursionlimit(20000)
    main()
