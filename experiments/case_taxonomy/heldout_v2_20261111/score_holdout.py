"""Holdout scoring (criteria v1 五、六, v2 四). Pure Python, reads results only.

    python score_holdout.py   -> score/score_cfg.json, score/score.json, score/stats.json, review.json

Detection, confirmation and score are those of difftest_tools_20261111/score.py (unchanged). confirm.json is filled
in the confirmation stage, after this first scoring (the first run sees no confirmations: every detection is
"not yet judged"). L01 failed to build and counts 0. review.json lists every detecting case for the manual review.
"""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
CANDS = ["L01", "L02", "L03", "L04", "L05", "L06", "L07", "L08", "L09", "L10"]
GROUPS = ["G0d", "G2d", "G3d", "G3c", "G3g"]
SEEDS = ["1", "2", "3"]
_s = importlib.util.spec_from_file_location("tools_score", CT / "difftest_tools_20261111" / "score.py")
SC = importlib.util.module_from_spec(_s)
_s.loader.exec_module(SC)


def main():
    done = [g for g in CANDS if (HERE / "logs" / f"{g}.warnings.done").exists()]
    conf = HERE / "confirm.json"
    if not conf.exists():
        conf.write_text("{}\n", encoding="utf8")
    d = HERE / "score"
    d.mkdir(exist_ok=True)
    samples = {g: {"compare": f"../cmp/{g}/compare.json", "lists": f"../ws/{g}/run/lists.json",
                   "pre": f"{g.lower()}_pre", "fix": f"{g.lower()}_fix"} for g in done}
    (d / "score_cfg.json").write_text(json.dumps({"groups": GROUPS, "seeds": SEEDS, "confirm": "../confirm.json",
                                                  "out": "score.json", "samples": samples}, indent=1))
    res = SC.run(d / "score_cfg.json")
    stats, review = {"candidates_done": done, "failed": [g for g in CANDS if g not in done], "noise": {}}, {}
    for g in done:
        cmp_ = SC.read_json(HERE / "cmp" / g / "compare.json")
        pre, fix = f"{g.lower()}_pre", f"{g.lower()}_fix"
        vp, vf = cmp_["checked"][pre]["verdicts"], cmp_["checked"][fix]["verdicts"]
        both = {i for i, v in vp.items() if v == "odd_loongarch" and vf.get(i) == "odd_loongarch"}
        cl = cmp_["checked"][pre]["clusters"].get("loongarch", {})
        stats["noise"][g] = {"cases_odd_pre_and_fix": len(both),
                             "clusters": sum(1 for m in cl.values() if both & set(map(str, m))),
                             "unstable": len(cmp_.get("unstable", []))}
        cases = {str(c["id"]): c for c in json.loads((HERE / "ws" / g / "run" / "cases.json").read_text())["cases"]}
        lists = json.loads((HERE / "ws" / g / "run" / "lists.json").read_text())
        det = SC.detecting(cmp_, pre, fix)
        review[g] = [{"id": i, "sc": cases[i]["sc"], "args": cases[i]["args"], "tmpl": cases[i].get("tmpl"),
                      "fvar": cases[i].get("fvar"),
                      "groups": sorted({f"{G}/{s}" for G in GROUPS for s in SEEDS if i in set(map(str, lists[G][s]))}),
                      "values": {k: v for k, v in cmp_["values"].get(i, {}).items()},
                      "verdict_pre": vp.get(i), "verdict_fix": vf.get(i)} for i in sorted(det, key=int)]
    stats["totals"] = res["totals"]
    (d / "stats.json").write_text(json.dumps(stats, indent=1, ensure_ascii=False), encoding="utf8")
    (HERE / "review.json").write_text(json.dumps(review, indent=1, ensure_ascii=False), encoding="utf8")
    print("noise", json.dumps(stats["noise"]))
    print("detecting cases", {g: len(v) for g, v in review.items()})


if __name__ == "__main__":
    main()
