"""Label address-capability differences with the probed limits (rtprobe criteria 四 + amendment 1). Pure Python.

    python tag_addr.py -> tag_stats.json, tag_clusters.json
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
M56 = (1 << 56) - 1


def limits(probes, kernels):
    out = {}
    for k in kernels:
        v = probes[k]["values"]
        assert probes[k]["complete"] and not probes[k]["unstable"] and not probes[k]["errors"], k
        out[k] = (int(v["uaccess_top"], 16), bool(v["top_byte_ignored"] or v["mm_top_byte_ignored"]))
    return out


def candidates(case):
    vs = []
    for t in case["args"]:
        if t.startswith("i:"):
            vs.append(int(t[2:], 16))
        else:
            m = re.match(r"o:[zag]:(\d+)$", t)
            if m:
                vs.append(1 << int(m.group(1)))
    return vs


def usable(v, lim):
    top, tbi = lim
    return (v & M56 if tbi else v) < top


def tagged(case, lims, rule=2):
    base = candidates(case)
    if rule == 1:  # criteria 四 as first written
        vs = set(base)
    else:  # amendment 2: pair sums (address + length) and extents 0 / 1 / one page
        sums = {(a + b) % 2**64 for i, a in enumerate(base) for j, b in enumerate(base) if i != j}
        vs = {(v + e) % 2**64 for v in set(base) | sums for e in (0, 1, 4096)}
    return any(len({usable(v, l) for l in lims.values()}) > 1 for v in vs)


def main():
    probes = json.loads((HERE / "probes.json").read_text())
    cmp_ = json.loads((CT / "anyarch_dev_20261110/runs/CURt/compare_any.json").read_text(encoding="utf8"))
    cases = {str(c["id"]): c for c in json.loads((CT / "diverse_dev_20261110/gen/cases_CUR.json").read_text())["cases"]}
    review = json.loads((CT / "oddarch_stats_20261110/review_CUR.json").read_text(encoding="utf8"))
    lims = limits(probes, cmp_["kernels"])
    s = cmp_["sets"]["cur_riscv"]
    vd = lambda i: s["verdicts"].get(i, "same")  # noqa: E731
    import sys
    rule = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    tag = {i: tagged(c, lims, rule) for i, c in cases.items()}
    by = {}
    for i in cases:
        b = by.setdefault(vd(i), {"cases": 0, "tagged": 0})
        b["cases"] += 1
        b["tagged"] += tag[i]
    clusters = []
    human = {(r["odd"], r["cluster"]): r["reason"] for r in review}
    ADDR = ("用户地址空间大小不同", "arm64 忽略地址最高字节")
    for a, cl in s["clusters"].items():
        for k, ids in cl.items():
            n = sum(tag[i] for i in ids)
            h = human.get((a, k))
            clusters.append({"odd": a, "cluster": k, "n_cases": len(ids), "tagged": n,
                             "label": "all" if n == len(ids) else ("none" if n == 0 else "mixed"),
                             "human_reason": h,
                             "agree": None if h is None else ((h in ADDR) == (n == len(ids)) and n in (0, len(ids)))})
    cs = {}
    for c in clusters:
        d = cs.setdefault(c["odd"], {"clusters": 0, "all": 0, "mixed": 0, "none": 0})
        d["clusters"] += 1
        d[c["label"]] += 1
    rev = [c for c in clusters if c["human_reason"] is not None]
    out = {"limits": {k: {"uaccess_top": format(v[0], "x"), "top_byte_ignored_any": v[1]} for k, v in lims.items()},
           "all_cases": {"cases": len(cases), "tagged": sum(tag.values())},
           "by_verdict": dict(sorted(by.items())), "clusters_by_arch": cs,
           "against_human_review": {"clusters": len(rev), "agree": sum(1 for c in rev if c["agree"]),
                                    "disagree": [c for c in rev if not c["agree"]]}}
    out["rule"] = rule
    (HERE / f"tag_stats_rule{rule}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf8")
    (HERE / f"tag_clusters_rule{rule}.json").write_text(json.dumps(clusters, indent=1, ensure_ascii=False), encoding="utf8")
    print(json.dumps(out["limits"]))
    print("all", out["all_cases"], "by verdict", json.dumps(out["by_verdict"]))
    print("clusters", json.dumps(cs))
    print("vs human review:", out["against_human_review"]["agree"], "/", len(rev))
    for c in out["against_human_review"]["disagree"]:
        print("  DISAGREE", c["odd"], c["cluster"], c["tagged"], "/", c["n_cases"], c["human_reason"])
    for c in clusters:
        if c["human_reason"] is None and c["odd"] != "riscv":
            print("  (no human label)", c["odd"], c["cluster"], c["label"])
    for c in clusters:
        if c["odd"] == "riscv":
            print("  riscv", c["cluster"], c["label"], c["n_cases"])


if __name__ == "__main__":
    main()
