"""Effect of the timeout class (plan item 0.1). Pure Python.

    python regress_timeout.py -> regress_timeout.json
 1. On the diverse logs (6 groups, normalised): the timeout class may only change cases in which some kernel timed out,
    and the set of detecting cases (checked riscv kernel: odd_riscv or weak_diff before the fix, same or weak_same after)
    must stay the same.
 2. On the debug-kernel run (dbgassert round): arm64 clusters with and without the class.
"""
import json
from pathlib import Path

import compare as N

HERE = Path(__file__).resolve().parent
CT = HERE.parent
GROUPS = ["CUR", "A101", "A310", "A171", "A181", "B467"]


def detecting(out, g):
    p = g.lower()
    pre, fix = out["checked"][f"{p}_pre"]["verdicts"], out["checked"][f"{p}_fix"]["verdicts"]
    return sorted((i for i, v in pre.items() if v in ("odd_riscv", "weak_diff")
                   and fix.get(i, "same") in ("same", "weak_same")), key=int)


def main():
    res = {"diverse": {}, "dbgassert": {}}
    for g in GROUPS:
        cfg = HERE / "regress" / f"kernels_{g}.json"
        c = json.loads(cfg.read_text())
        c["out"] = f"{g}_tc_off"
        cfg.write_text(json.dumps(c, indent=1))
        off = N.run(cfg, tclass=False)
        c["out"] = f"{g}_tc_on"
        cfg.write_text(json.dumps(c, indent=1))
        on = N.run(cfg, tclass=True)
        row = {}
        for k in on["checked"]:
            vo, vn = off["checked"][k]["verdicts"], on["checked"][k]["verdicts"]
            ch = [i for i in set(vo) | set(vn) if vo.get(i, "same") != vn.get(i, "same")]
            moves = {}
            for i in ch:
                m = f"{vo.get(i, 'same')} -> {vn.get(i, 'same')}"
                moves[m] = moves.get(m, 0) + 1
            row[k] = {"changed": len(ch), "moves": dict(sorted(moves.items())),
                      "clusters_off": {a: len(x) for a, x in off["checked"][k]["clusters"].items()},
                      "clusters_on": {a: len(x) for a, x in on["checked"][k]["clusters"].items()}}
        if g != "CUR":
            d0, d1 = detecting(off, g), detecting(on, g)
            row["detecting"] = {"off": len(d0), "on": len(d1), "same_set": d0 == d1,
                                "lost": sorted(set(d0) - set(d1), key=int), "gained": sorted(set(d1) - set(d0), key=int)}
        res["diverse"][g] = row
    cfg = CT / "dbgassert_dev_20261111" / "kernels_dbg.json"
    c = json.loads(cfg.read_text())
    tmp = HERE / "regress" / "kernels_dbg.json"
    for tag, tc in (("off", False), ("on", True)):
        c2 = dict(c, cases="../" + c["cases"], logs="../../dbgassert_dev_20261111/" + c["logs"],
                  volatile="../" + c["volatile"], out=f"dbg_tc_{tag}")
        tmp.write_text(json.dumps(c2, indent=1))
        o = N.run(tmp, tclass=tc)
        s = o["checked"]["dbg_riscv"]
        res["dbgassert"][tag] = {"summary": s["summary"], "clusters": {a: len(x) for a, x in s["clusters"].items()}}
    (HERE / "regress_timeout.json").write_text(json.dumps(res, indent=1))
    for g, row in res["diverse"].items():
        print(g, {k: (v["changed"], v["moves"]) for k, v in row.items() if k != "detecting"}, row.get("detecting"))
    print(json.dumps(res["dbgassert"]))


if __name__ == "__main__":
    main()
