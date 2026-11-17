"""Regression of compare.py against the earlier rounds, on the stored logs. Pure Python.

    python regress.py -> regress/…, regress_result.json
 1. raw mode        == diverse_dev_20261110/runs/<g>/compare.json            (riscv-only verdicts, mapped)
 2. normalised mode == stability_dev_20261111/ev_diverse/runs/<g>/compare.json
 3. raw mode        == anyarch_dev_20261110/regress/old_<g>/compare_any.json  (three directions, where defined)
 4. learn           == stability_dev_20261111/volatile.json
"""
import json
from pathlib import Path

import compare as N

HERE = Path(__file__).resolve().parent
CT = HERE.parent
GROUPS = ["CUR", "A101", "A310", "A171", "A181", "B467"]


def kernels(g):
    if g == "CUR":
        return [{"name": "cur_riscv", "arch": "riscv"}, {"name": "cur_arm64", "arch": "arm64"},
                {"name": "cur_x86_64", "arch": "x86_64"}]
    p = g.lower()
    return [{"name": f"{p}_pre", "arch": "riscv"}, {"name": f"{p}_fix", "arch": "riscv"},
            {"name": f"{p}_ref_arm64", "arch": "arm64"}, {"name": f"{p}_ref_x86_64", "arch": "x86_64"}]


def old_class(v):
    return {"consistent": "same", "odd_strong": "odd_self", "odd_weak": "weak_diff", "ref_split": "others_differ",
            "excluded_cap": "excluded", "excluded_env": "excluded", "no_ref": "no_ref", "unstable": "unstable"}[v]


def new_class(v):
    if v in ("same", "weak_same"):
        return "same"
    if v == "odd_riscv":
        return "odd_self"
    if v.startswith("odd_") or v == "split":
        return "others_differ"
    return v


def main():
    (HERE / "regress").mkdir(exist_ok=True)
    res = {"raw_vs_diverse": {}, "norm_vs_stability": {}, "raw_vs_anyarch": {}}
    cfgs = []
    for g in GROUPS:
        cfg = {"group": g, "cases": f"../../diverse_dev_20261110/gen/cases_{g}.json",
               "logs": f"../../diverse_dev_20261110/runs/{g}", "out": f"{g}_norm",
               "volatile": "../../stability_dev_20261111/volatile.json", "kernels": kernels(g)}
        p = HERE / "regress" / f"kernels_{g}.json"
        p.write_text(json.dumps(cfg, indent=1))
        cfgs.append(p)
        ids = [str(c["id"]) for c in json.loads((CT / f"diverse_dev_20261110/gen/cases_{g}.json").read_text())["cases"]]
        for tag, raw, ref in (("raw_vs_diverse", True, CT / f"diverse_dev_20261110/runs/{g}/compare.json"),
                              ("norm_vs_stability", False, CT / f"stability_dev_20261111/ev_diverse/runs/{g}/compare.json")):
            cfg["out"] = f"{g}_{'raw' if raw else 'norm'}"
            p.write_text(json.dumps(cfg, indent=1))
            new = N.run(p, raw=raw, tclass=False)  # the earlier rounds had no timeout class
            old = json.loads(ref.read_text())
            bad = {}
            for rk, ov in old["verdicts"].items():
                nv = new["checked"][rk]["verdicts"]
                for i in ids:
                    a, b = old_class(ov[i]), new_class(nv.get(i, "same"))
                    if a != b:
                        bad.setdefault(f"{rk}: {ov[i]} vs {nv.get(i, 'same')}", []).append(i)
            res[tag][g] = {"mismatch": {k: len(v) for k, v in bad.items()}}
            if raw:
                any_ = json.loads((CT / f"anyarch_dev_20261110/regress/old_{g}/compare_any.json").read_text(encoding="utf8"))
                bad2 = 0
                for rk, s in any_["sets"].items():
                    if new["kernels"][rk] != "riscv":
                        continue
                    for i in ids:
                        a, b = s["verdicts"].get(i, "same"), new["checked"][rk]["verdicts"].get(i, "same")
                        if a == "excluded":  # anyarch excluded the whole case; the new rule may still compare weakly
                            continue
                        bad2 += a != b
                    cl_old = {x: sorted(c) for x, c in s["clusters"].items()}
                    cl_new = {x: sorted(c) for x, c in new["checked"][rk]["clusters"].items()}
                    bad2 += cl_old != cl_new
                res["raw_vs_anyarch"][g] = {"mismatch": bad2}
    learned = N.learn(cfgs, HERE / "regress" / "volatile_relearned.json")
    ref = json.loads((CT / "stability_dev_20261111/volatile.json").read_text())
    res["learn_equal"] = learned["slots"] == ref["slots"] and learned["returns"] == ref["returns"]
    res["all_ok"] = (res["learn_equal"] and all(not v["mismatch"] for t in ("raw_vs_diverse", "norm_vs_stability")
                                                 for v in res[t].values())
                     and all(v["mismatch"] == 0 for v in res["raw_vs_anyarch"].values()))
    (HERE / "regress_result.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
