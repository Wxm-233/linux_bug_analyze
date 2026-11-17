"""stats.json for static2_dev_20261109.   python make_stats.py"""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
a = json.loads((HERE / "ablation.json").read_text())
b = json.loads((HERE / "baseline_check.json").read_text())
e = json.loads((HERE / "evaluation.json").read_text())
r1 = json.loads((HERE.parent / "semhint_dev_20261109" / "evaluation.json").read_text())
C = ["base", "fix", "I1", "I2", "I3", "I4", "all"]
st = {"round": "static2_dev_20261109",
      "criteria_sha256": (HERE / "criteria_sha256.txt").read_text().split()[0],
      "selftest": "pass (third run; first two: my fixture missing a declaration, then amendment 1)",
      "baseline_reproduction": b,
      "ablation": {g: {c: {k: a[g][c][k] for k in ("sites", "T", "reach_map", "fixpoint", "samples") if k in a[g][c]}
                       for c in C} for g in a},
      "units": {g: a[g]["units"] for g in a},
      "b467_fix_functions": a["B467"]["fix_functions"],
      "callbacks_all_CUR": a["CUR"]["all"]["callbacks"],
      "tree_boundary_all": {g: a[g]["all"]["tree_boundary"] for g in a},
      "dynamic": {"this_round": {G: {k: e["totals"][G][k] for k in ("confirmed_total", "median_cost", "seeds_detecting")}
                                  for G in ("G2", "G3")},
                  "round1": {G: {k: r1["totals"][G][k] for k in ("confirmed_total", "median_cost")}
                             for G in ("G0", "G1", "G2", "G3")},
                  "current": {G: e["current"][G] for G in ("G2", "G3")},
                  "current_clusters": e["current"]["clusters_total"]},
      "model_calls": 0, "builds": 0, "new_confirmed_bugs": 0, "new_suspects": 0}
(HERE / "stats.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
print("ok")
