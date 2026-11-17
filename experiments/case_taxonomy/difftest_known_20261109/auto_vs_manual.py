"""Criteria section 8, second item: automatic exclusion vs the manual classification of round difftest_proto_20261109.

    python auto_vs_manual.py   -> auto_vs_manual.json

For each test key on which the three current kernels differed in the previous round, the automatic rule says:
the kernels that do not meet the test's prerequisite are excluded (kind from their .config); if the remaining
kernels agree, the difference is fully explained by those exclusions.
"""
import json
from pathlib import Path

import compare2

HERE = Path(__file__).resolve().parent
PROTO = HERE.parent / "difftest_proto_20261109" / "stats.json"
CUR = ["cur_riscv", "cur_arm64", "cur_x86_64"]


def main():
    proto = json.loads(PROTO.read_text(encoding="utf-8"))
    cmp = json.loads((HERE / "runs" / "all" / "compare2.json").read_text(encoding="utf-8"))
    truth = json.loads((HERE / "truth.json").read_text())
    rows, agree = [], 0
    for key, rec in proto["current_differences"].items():
        test = key.split("/", 1)[1]
        vals = {k: rec["values"][k] for k in CUR}
        if len(set(vals.values())) == 1:
            continue  # only differed between the B467 kernels, not among the current ones
        manual = rec["class"]
        need = compare2.NEEDS.get(test)
        excluded = {}
        for k in CUR:
            if need and cmp["kernels"][k]["capabilities"].get(need) == "unmet":
                excluded[k] = compare2.exclusion_kind(need, k, truth)
        rest = {k: v for k, v in vals.items() if k not in excluded}
        explained = len(set(rest.values())) <= 1
        auto = "/".join(sorted(set(excluded.values()))) if explained and excluded else "未解释"
        # the new run must reproduce last round's values for the comparison to be meaningful
        same_values = all(cmp["kernels"][k]["results"].get(test) == vals[k] for k in CUR)
        ok = auto == manual
        agree += ok
        rows.append({"test": test, "values": vals, "manual": manual, "auto": auto, "excluded": excluded,
                     "need": need, "agree": ok, "values_reproduced_this_round": same_values})
    out = {"rows": rows, "agree": agree, "total": len(rows)}
    (HERE / "auto_vs_manual.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in rows:
        print(r["test"], r["manual"], r["auto"], r["excluded"], r["values_reproduced_this_round"])
    print(f"agree {agree}/{len(rows)}")


if __name__ == "__main__":
    main()
