"""stats.json for this round (criteria 十一).   python make_stats.py"""
import gzip
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
GROUPS = ["A101", "A310", "A171", "A181", "B467", "CUR"]
ev = json.loads((HERE / "evaluation.json").read_text())
st = {"round": "semhint_dev_20261109", "criteria_sha256": (HERE / "criteria_sha256.txt").read_text().split()[0],
      "budget_per_group_seed": 1000, "seeds": 3, "groups": {}, "evaluation": {k: ev[k] for k in
      ("totals", "verdict_G3", "verdict_G2_vs_G1")}, "current": ev["current"], "samples": {}}
for g in GROUPS:
    h = json.loads((HERE / "gen" / f"hints_{g}.json").read_text())
    m = json.loads((HERE / "gen" / f"cases_{g}.json").read_text())
    c = json.loads((HERE / "runs" / g / "compare.json").read_text())
    st["groups"][g] = {"static": h["stats"], "U": len(m["U"]), "T": len(m["T"]), "cases_union": len(m["cases"]),
                       "excluded": {k: len(v) for k, v in m["excluded"].items()},
                       "unstable": len(c["unstable"]), "summary": c["summary"], "complete": c["complete"],
                       "taint_changed": c["taint_changed"], "harness_errors": c["harness_errors"]}
for x, s in ev["samples"].items():
    st["samples"][x] = {k: s[k] for k in ("detecting_ids", "detecting_strong", "patch_attributable_diff",
                                          "coverage")}
    st["samples"][x]["first_detect"] = {G: [s["per_group"][G][sd]["first_detect"] for sd in ("1", "2", "3")]
                                        for G in s["per_group"]}
    st["samples"][x]["cond_cases"] = {G: [s["per_group"][G][sd]["cond_cases"] for sd in ("1", "2", "3")]
                                      for G in s["per_group"]}
st["reach"] = None  # criteria 八: not measured this round
st["model_calls"] = 0
st["codex_calls"] = 1
(HERE / "stats.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
print("ok")
