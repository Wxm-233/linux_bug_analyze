"""Rebuild sample_eval.json from results/ and attribute every miss (descriptive, after scoring).

    python3 miss_analysis.py   -> sample_eval.json, miss_analysis.json

For each fix function of a sample (criteria section 5), record mechanically:
  candidate      the name is in the candidate pools (criteria 3.1)
  riscv_impl     the pre-fix riscv facts have an implementation (non-static, or static in a .h)
  riscv_static_c the pre-fix riscv facts only have a static definition in a .c file
  counterparts   which of x86 / arm64 (current) have an implementation
and derive the stage at which the sample dropped out:
  not_candidate  no fix function is a candidate
  no_riscv_impl  candidates, but riscv has no implementation of any of them (e.g. static in .c)
  no_counterpart riscv implementations exist, but neither counterpart implements any of them
  compared       at least one family was compared; then flags_on_fix_functions tells whether anything was raised
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import xcmp  # noqa: E402
from eval_samples import EVALUABLE, POOLS, WORK, CUR  # noqa: E402


def main():
    results = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (HERE / "results").glob("*.json")}
    evals = [results[s] for s in EVALUABLE]
    (HERE / "sample_eval.json").write_text(json.dumps(evals, ensure_ascii=False, indent=1), encoding="utf-8")
    cands, _ = xcmp.candidates_from_pools(POOLS)
    cb = {t: xcmp.Build(xcmp.load(str(CUR / f"facts_{t}.json.gz"))) for t in ("x86", "arm64")}
    out = []
    for r in evals:
        rb = xcmp.Build(xcmp.load(str(WORK / "facts" / r["id"] / "facts_riscv.json.gz")))
        fns = []
        for n in r["fix_functions"]:
            defs = rb.by_name.get(n, [])
            fns.append({"name": n, "candidate": n in cands, "riscv_impl": bool(rb.impls(n)),
                        "riscv_static_c": bool(defs) and not rb.impls(n),
                        "counterparts": [t for t, b in cb.items() if b.impls(n)]})
        if not any(f["candidate"] for f in fns):
            stage = "not_candidate"
        elif not any(f["candidate"] and f["riscv_impl"] for f in fns):
            stage = "no_riscv_impl"
        elif not any(f["candidate"] and f["riscv_impl"] and f["counterparts"] for f in fns):
            stage = "no_counterpart"
        else:
            stage = "compared"
        out.append({"id": r["id"], "class": r["class"], "hit": r["hit"], "stage": stage,
                    "flags_on_fix_functions": [(f["type"], f["family"], f["detail"]) for f in r["flags_on_fix_functions"]],
                    "fix_functions": fns})
    (HERE / "miss_analysis.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for o in out:
        print(o["id"], o["class"], "HIT" if o["hit"] else "miss", o["stage"], o["flags_on_fix_functions"][:2],
              [(f["name"], f["candidate"], f["riscv_impl"], f["counterparts"]) for f in o["fix_functions"]][:3])


if __name__ == "__main__":
    main()
