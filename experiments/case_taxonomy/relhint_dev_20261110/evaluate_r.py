"""Detection and current-version noise for G3d vs G3r (relhint criteria 三、四). Pure Python.

    python evaluate_r.py -> evaluation.json, review_detect.json, review_current.json, stats.json
Uses the original evaluate_d.py logic with only the directory and the group names replaced.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "diverse_dev_20261110"))
sys.path.insert(0, str(CT / "anyarch_dev_20261110"))
import evaluate_d as E  # noqa: E402
import compare_any as CA  # noqa: E402

E.HERE = HERE
E.GROUPS = ["G3d", "G3r"]


def main():
    E.main()
    ev = json.loads((HERE / "evaluation.json").read_text())
    old = json.loads((CT / "diverse_dev_20261110" / "evaluation.json").read_bytes().decode("utf8", "replace"))
    # three directions on CUR
    cfg = {"group": "CUR", "cases": "gen/cases_CUR.json", "lists": None, "logs": "runs/CUR", "out": "runs/CUR",
           "kernels": [{"name": "cur_riscv", "arch": "riscv"}, {"name": "cur_arm64", "arch": "arm64"},
                       {"name": "cur_x86_64", "arch": "x86_64"}]}
    (HERE / "kernels_CUR.json").write_text(json.dumps(cfg, indent=1))
    ca = CA.run(HERE / "kernels_CUR.json")["sets"]["cur_riscv"]
    lists = json.loads((HERE / "gen" / "lists_CUR.json").read_text())
    cur = {}
    for G in E.GROUPS:
        ids = {str(i) for s in lists[G] for i in lists[G][s]}
        d = {"cases": len(ids)}
        for a, cl in ca["clusters"].items():
            d[a] = {"cases": sum(1 for i in ids if ca["verdicts"].get(i) == "odd_" + a),
                    "clusters": sum(1 for m in cl.values() if ids & set(m))}
        d["split"] = sum(1 for i in ids if ca["verdicts"].get(i) == "split")
        d["unstable"] = sum(1 for i in ids if ca["verdicts"].get(i) == "unstable")
        d["clusters_total"] = sum(d[a]["clusters"] for a in ca["clusters"])
        cur[G] = d
    meta = {g: json.loads((HERE / "gen" / f"cases_{g}.json").read_text())["rel"]
            for g in ["CUR"] + E.SAMPLES}
    tot = ev["totals"]
    covered = {G: sum(1 for x in E.SAMPLES if tot[G]["seeds_detecting"][x]) for G in E.GROUPS}
    ok = (tot["G3r"]["confirmed_total"] >= tot["G3d"]["confirmed_total"] - 1 and covered["G3r"] >= covered["G3d"]
          and cur["G3r"]["clusters_total"] <= cur["G3d"]["clusters_total"])
    stats = {"totals": {G: {"confirmed_total": tot[G]["confirmed_total"], "detect_total": tot[G]["detect_total"],
                            "seeds_detecting": tot[G]["seeds_detecting"], "defects_covered": covered[G]}
                        for G in E.GROUPS},
             "diverse_round_G3d": {"confirmed_total": old["totals"]["G3d"]["confirmed_total"],
                                   "seeds_detecting": old["totals"]["G3d"]["seeds_detecting"]},
             "current_three_directions": cur, "relative_cases": {g: {k: m[k] for k in (
                 "relative_cases", "limit_hint_cases_in_G3d", "kinds")} for g, m in meta.items()},
             "reference_line_merge_ok": ok}
    (HERE / "stats.json").write_text(json.dumps(stats, indent=1, ensure_ascii=False), encoding="utf8")
    print(json.dumps(stats, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
