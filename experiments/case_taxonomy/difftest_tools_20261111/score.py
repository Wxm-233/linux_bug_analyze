"""Detection score from the new-format comparison results (plan item 0.3). Pure Python.

    python score.py <score.json>  -> prints and writes <out>

score.json (paths relative to it):
  {"groups": ["G3d", ...], "seeds": ["1", "2", "3"], "confirm": <confirm.json>, "out": <file>,
   "samples": {"A101": {"compare": <compare.json>, "lists": <lists json>, "pre": "a101_pre", "fix": "a101_fix"}, ...}}

A case detects a sample when, for the checked kernel before the fix, the verdict is odd_<its own architecture> or
weak_diff, and for the kernel after the fix it is same or weak_same.  (This is the earlier rule "odd before, consistent
after" expressed in the new verdicts.)  A detection counts as confirmed when confirm.json lists the case with ok = true.
Score of a group = number of (sample, seed) pairs whose list contains at least one confirmed detecting case.
"""
import json
import sys
from pathlib import Path


def read_json(p):
    b = Path(p).read_bytes()
    try:
        return json.loads(b.decode("utf8"))
    except UnicodeDecodeError:
        return json.loads(b.decode("gbk"))  # confirm.json of the earlier rounds was written in the system code page


def detecting(cmp_, pre, fix):
    arch = cmp_["kernels"][pre]
    vp, vf = cmp_["checked"][pre]["verdicts"], cmp_["checked"][fix]["verdicts"]
    return {i for i, v in vp.items() if v in ("odd_" + arch, "weak_diff") and vf.get(i, "same") in ("same", "weak_same")}


def run(cfg_path):
    cfg_path = Path(cfg_path).resolve()
    cfg, base = read_json(cfg_path), cfg_path.parent
    confirm = read_json(base / cfg["confirm"])
    seeds, groups = cfg["seeds"], cfg["groups"]
    per, det_n = {}, {}
    for x, s in cfg["samples"].items():
        cmp_ = read_json(base / s["compare"])
        lists = read_json(base / s["lists"])
        det = detecting(cmp_, s["pre"], s["fix"])
        ok = {i for i, v in confirm.get(x, {}).items() if v.get("ok")}
        det_n[x] = {"detecting": len(det), "confirmed": len(det & ok),
                    "unconfirmed": sorted(det - set(confirm.get(x, {})), key=int)}
        per[x] = {}
        for G in groups:
            per[x][G] = {}
            for sd in seeds:
                ids = [str(i) for i in lists[G][sd]]
                per[x][G][sd] = {
                    "first_detect": next((n + 1 for n, i in enumerate(ids) if i in det), None),
                    "first_confirmed": next((n + 1 for n, i in enumerate(ids) if i in det and i in ok), None),
                    "detecting_cases": sum(1 for i in ids if i in det)}
    tot = {}
    for G in groups:
        sd_det = {x: sum(1 for sd in seeds if per[x][G][sd]["first_confirmed"]) for x in per}
        tot[G] = {"confirmed_total": sum(sd_det.values()),
                  "detect_total": sum(1 for x in per for sd in seeds if per[x][G][sd]["first_detect"]),
                  "seeds_detecting": sd_det, "defects_covered": sum(1 for v in sd_det.values() if v),
                  "defects_in_2_seeds": sum(1 for v in sd_det.values() if v >= 2)}
    out = {"totals": tot, "samples": det_n, "per_seed": per}
    if cfg.get("out"):
        (base / cfg["out"]).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf8")
    for G in groups:
        print(G, json.dumps(tot[G]))
    for x, d in det_n.items():
        print("  ", x, d["detecting"], "detecting,", d["confirmed"], "confirmed; not yet judged:", d["unconfirmed"][:20])
    return out


if __name__ == "__main__":
    run(sys.argv[1])
