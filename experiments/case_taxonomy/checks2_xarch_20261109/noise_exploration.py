"""Post-hoc noise exploration for the NEXT round (not part of this round's verdict; criteria are unchanged).

    python3 noise_exploration.py   -> noise_exploration.json

Applies candidate filters to flags_current.json and to every sample's flags, and reports how many flags each filter
keeps, which manually reviewed flags survive, and which sample hits survive. Written after the manual review, so any
filter chosen from it must be written into the next round's criteria before being evaluated there.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def generic(loc):
    """a definition outside arch/ (common default, __weak, asm-generic)"""
    return not loc.startswith("arch/")


def f_stub_all_counterparts(f):
    """stub only when every counterpart that has the family implements it (and there are at least two)"""
    return f["type"] != "stub" or len(f["counterparts"]) >= 2


def f_no_param_keys(f):
    return not (f["type"] == "write-missing" and "p#" in f["detail"])


def f_not_single_arch_feature(f):
    """drop families where riscv only has a generic definition and exactly one counterpart has an arch one"""
    rv_generic = all(generic(l) for l in f["riscv"])
    arch_cps = [t for t, locs in f["counterparts"].items() if any(not generic(l) for l in locs)]
    return not (rv_generic and len(arch_cps) == 1)


FILTERS = {"stub_needs_both": f_stub_all_counterparts, "no_param_keys": f_no_param_keys,
           "not_single_arch_feature": f_not_single_arch_feature}


def apply(flags, names):
    return [f for f in flags if all(FILTERS[n](f) for n in names)]


def main():
    cur = json.loads((HERE / "flags_current.json").read_text(encoding="utf-8"))["flags"]
    review = json.loads((HERE / "manual_review.json").read_text(encoding="utf-8"))["items"]
    key = lambda f: (f["type"], f["family"], f["detail"])
    rev = {key(i): i["verdict"] for i in review}
    samples = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((HERE / "results").glob("*.json"))]
    combos = [[], ["stub_needs_both"], ["no_param_keys"], ["not_single_arch_feature"],
              ["no_param_keys", "not_single_arch_feature"], list(FILTERS)]
    out = []
    for c in combos:
        kept = apply(cur, c)
        kk = {key(f) for f in kept}
        rv_kept = {v: sum(1 for k, vv in rev.items() if vv == v and k in kk) for v in set(rev.values())}
        hits = {s["id"]: bool(apply(s.get("hit_flags", []), c)) for s in samples if s.get("status") == "ok"}
        out.append({"filters": c, "current_distinct": len(kept), "reviewed_kept_by_verdict": rv_kept,
                    "sample_hits_kept": sum(hits.values()), "sample_hits_before": sum(1 for s in samples if s.get("hit")),
                    "hit_ids_kept": sorted(k for k, v in hits.items() if v)})
    (HERE / "noise_exploration.json").write_text(json.dumps({"note": __doc__.strip(), "results": out},
                                                             ensure_ascii=False, indent=1), encoding="utf-8")
    for r in out:
        print(r["filters"] or ["(none)"], r["current_distinct"], r["reviewed_kept_by_verdict"],
              f"hits {r['sample_hits_kept']}/{r['sample_hits_before']}")


if __name__ == "__main__":
    main()
