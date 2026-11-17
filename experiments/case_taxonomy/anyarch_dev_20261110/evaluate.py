"""Before/after comparison of the constant translation on CUR (anyarch criteria 四). Pure Python.

    python evaluate.py -> stats.json, changes_CUR.json
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    old = json.loads((HERE / "regress" / "old_CUR" / "compare_any.json").read_text(encoding="utf8"))
    new = json.loads((HERE / "runs" / "CURt" / "compare_any.json").read_text(encoding="utf8"))
    ap = json.loads((HERE / "gen" / "apply_stats.json").read_text())
    cal = json.loads((HERE / "gen" / "confirmed.json").read_text())
    cc = json.loads((HERE / "gen" / "calib_cases.json").read_text())
    consts = json.loads((HERE / "gen" / "consts_CUR.json").read_text())
    cases = {str(c["id"]): c for c in json.loads(
        (HERE.parent / "diverse_dev_20261110" / "gen" / "cases_CUR.json").read_text())["cases"]}
    so, sn = old["sets"]["cur_riscv"], new["sets"]["cur_riscv"]
    vo = lambda i: so["verdicts"].get(i, "same")  # noqa: E731
    vn = lambda i: sn["verdicts"].get(i, "same")  # noqa: E731
    moved = {}
    for i in cases:
        if vo(i) != vn(i):
            moved.setdefault(f"{vo(i)} -> {vn(i)}", []).append(i)
    changed = [str(i) for i in ap["changed_ids"]["arm64"]]
    ko = {a: set(c) for a, c in so["clusters"].items()}
    kn = {a: set(c) for a, c in sn["clusters"].items()}
    stats = {
        "probe": consts["stats"],
        "divergent_constants": consts["divergent"],
        "candidate_families": sorted(cc["families"]), "rejected_by_filter": cc["rejected_by_filter"],
        "calibration_cases": len(cc["cases"]), "confirmed": cal["confirmed"],
        "calibration_detail": {k: {"support": len(v["support"]), "against": len(v["against"]),
                                   "neutral": v["neutral"], "skipped": v["skipped"]}
                               for k, v in cal["detail"].items()},
        "translated_cases": ap["stats"],
        "before": {"summary": so["summary"], "clusters": {a: len(c) for a, c in so["clusters"].items()}},
        "after": {"summary": sn["summary"], "clusters": {a: len(c) for a, c in sn["clusters"].items()}},
        "clusters_gone": {a: sorted(ko[a] - kn.get(a, set())) for a in ko},
        "clusters_new": {a: sorted(kn[a] - ko.get(a, set())) for a in kn},
        "verdict_moves": {k: len(v) for k, v in sorted(moved.items())},
        "translated_case_verdicts": {i: [vo(i), vn(i)] for i in changed},
        "moves_outside_translated": {k: [i for i in v if i not in changed] for k, v in sorted(moved.items())
                                     if any(i not in changed for i in v)},
        "line": "模型调用 0；构建 0；新确认缺陷 0；新疑点 待核对",
    }
    (HERE / "stats.json").write_text(json.dumps(stats, indent=1, ensure_ascii=False), encoding="utf8")
    det = []
    for k, ids in sorted(moved.items()):
        for i in ids:
            det.append({"id": i, "move": k, "translated": i in changed, "sc": cases[i]["sc"], "args": cases[i]["args"],
                        "before": old["values"].get(i), "after": new["values"].get(i)})
    (HERE / "changes_CUR.json").write_text(json.dumps(det, indent=1, ensure_ascii=False), encoding="utf8")
    for k in ("translated_cases", "before", "after", "clusters_gone", "clusters_new", "verdict_moves",
              "translated_case_verdicts"):
        print(k, json.dumps(stats[k], ensure_ascii=False))
    print("moves outside translated cases:", {k: len(v) for k, v in stats["moves_outside_translated"].items()})


if __name__ == "__main__":
    main()
