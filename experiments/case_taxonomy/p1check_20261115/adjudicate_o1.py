"""Agreement on the 30 O1 findings (Claude vs Codex blind) and my adjudication -> o1_adjudication.json, stats.json"""
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
C = ["可能", "说不清", "不可能"]
ADJ = {
    6: ("可能", "采纳 Codex：page_vma_mapped_walk 的 check_pte 在非迁移模式下接受 device-exclusive 项；folio_referenced_one 拿到 pvmw.pte 后不查 present 就走 "
               "clear_flush_young_ptes_notify → ptep_clear_flush_young → 通用 ptep_test_and_clear_young → pte_young。git 历史里没有对应的 device-exclusive 修复"
               "（同系列修过 page_idle、try_to_unmap_one 等）。我核实了这两段代码，没核实 device-exclusive 的 folio 是否真会进入回收。新疑点 2，待核实。"),
    7: ("不可能", "采纳 Codex：PMD 老化的各调用点在锁内查过 present；回收 rmap 路径不接受 PMD 迁移项；device-exclusive 只有 PTE 级。"),
}


def main():
    me = {x["k"]: x for x in json.loads((HERE / "review_o1_judgement.json").read_text(encoding="utf-8"))["items"]}
    cx = {x["k"]: x for x in json.loads((HERE / "codex_blind/codex_o1.json").read_text(encoding="utf-8"))}
    tab = Counter((me[k]["verdict"], cx[k]["verdict"]) for k in me)
    n = len(me)
    po = sum(tab[(a, a)] for a in C) / n
    pe = sum((sum(tab[(a, b)] for b in C) / n) * (sum(tab[(b, a)] for b in C) / n) for a in C)
    dis = sorted(k for k in me if me[k]["verdict"] != cx[k]["verdict"])
    assert dis == sorted(ADJ), dis
    rows = []
    for k in sorted(me):
        v, why = ADJ.get(k, (me[k]["verdict"], "两人一致"))
        rows.append({"k": k, "loc": me[k]["loc"], "claude": me[k]["verdict"], "codex": cx[k]["verdict"], "final": v, "adjudication": why})
    fin = Counter(r["final"] for r in rows)
    out = {"n": n, "raw_agreement": round(po, 3), "cohen_kappa": round((po - pe) / (1 - pe), 3),
           "table_claude_rows_codex_cols": {a: {b: tab[(a, b)] for b in C} for a in C}, "final": dict(fin),
           "suspects": ["fs/proc/task_mmu.c:1129 smaps_pmd_entry 对非 present PMD 读 pmd_young/pmd_dirty（两人都判可能）",
                        "include/linux/pgtable.h:534 经 folio_referenced_one 对 device-exclusive PTE 清 young（Codex 提出，我部分核实）"],
           "rows": rows}
    (HERE / "o1_adjudication.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

    head = json.loads((HERE / "head.json").read_text())
    dev = json.loads((HERE / "dev.json").read_text())
    ho = json.loads((HERE / "heldout_score.json").read_text())
    hs = json.loads((HERE / "heldout_set.json").read_text())
    stats = {
        "selftest_cases": 32, "selftest": "PASS",
        "dev": {c: {"hit": all(r["hit"] for r in rows_), "gone_after_fix": all(r["gone_after_fix"] for r in rows_)} for c, rows_ in dev.items()},
        "heldout": {"scanned": hs["scanned"], "selected": hs["selected"], "excluded_read": hs["excluded_read"], "n": ho["n"], "hit": ho["hit"],
                    "gone_after_fix": ho["gone_after_fix"],
                    "miss_reasons": {"not_P1_shape_check_added_with_accessor": 6, "scoring_artifact_reported_other_accessor_or_callee": 2}},
        "head": {"findings": len(head["findings"]), "by_origin": head["by_origin"], "files": head["files_with_accessors"],
                 "functions": head["functions"], "parse_errors": head["parse_errors"]},
        "o1_top30": {"claude_codex_agreement": out["raw_agreement"], "kappa": out["cohen_kappa"], "final": dict(fin)},
        "extra_codex_p1_samples": {"bd1f2b2ace84": "hit, gone", "65529295607f": "hit, partly gone", "3faa3ebc89c1": "out of accessor list"},
        "model_calls": 0, "codex_calls": 2, "builds": 0, "new_bugs": 0, "new_suspects": 2,
    }
    (HERE / "stats.json").write_text(json.dumps(stats, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("raw_agreement", "cohen_kappa", "final")}, ensure_ascii=False))
    print(json.dumps(stats["dev"]), stats["heldout"]["hit"], "/", stats["heldout"]["n"])


if __name__ == "__main__":
    main()
