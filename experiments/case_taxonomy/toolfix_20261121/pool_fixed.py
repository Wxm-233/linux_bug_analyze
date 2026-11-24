"""toolfix criteria 四: rerun the whole WT pool (the entries of wtrange2_20261121/pool_rng.json) with the fixed rng.py. WSL.
    python3 pool_fixed.py -> pool_rng_fixed.json + diff_wt.json + summary
"""
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(HERE))
import bind2 as B2  # noqa: E402
import rng as R  # noqa: E402

B = B2.B


def main():
    old = {x["id"]: x for x in json.loads((CT / "wtrange2_20261121/pool_rng.json").read_text(encoding="utf-8"))}
    rows = {r["id"]: r for r in B.unreviewed()}
    out = []
    for i in old:
        r = rows.get(i)
        if r is None:
            out.append({"id": i, "overall": "未找到条目", "per_build": {}, "missing": []})
            continue
        us = B2.units(r["file"], r["func"])
        src_text = B2.git("show", f"{B.REV}:{r['file']}")
        per, missing = R.assess(dict(r, units=us), src_text)
        out.append({"id": i, "overall": R.overall(per, missing), "per_build": per, "missing": missing})
        print(i, "->", out[-1]["overall"], flush=True)
    (HERE / "pool_rng_fixed.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    diff = [{"id": x["id"], "old": old[x["id"]]["overall"], "fixed": x["overall"], "missing": x["missing"]}
            for x in out if old[x["id"]]["overall"] != x["overall"]]
    (HERE / "diff_wt.json").write_text(json.dumps(diff, indent=1, ensure_ascii=False))
    print(json.dumps({"entries": len(out), "old": dict(Counter(x["overall"] for x in old.values())),
                      "fixed": dict(Counter(x["overall"] for x in out)),
                      "changed": dict(Counter(f"{d['old']} -> {d['fixed']}" for d in diff))}, ensure_ascii=False))


if __name__ == "__main__":
    sys.setrecursionlimit(100000)
    main()
