"""Two-annotator agreement and my adjudication (added 2026-11-15 after Codex's blind judgement).

    python adjudicate.py   -> agreement.json, adjudication.json
Inputs: judgement.json (Claude, unchanged), codex_blind/codex_judgement.json (Codex gpt-6.1-sol max, blind, read full patches).
The final call on each disagreement is mine; reasons below.
"""
import json
import math
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATS = ["是", "说不清", "不是"]

# disagreements -> (final verdict, pattern if 是, reason)
ADJ = {
    "099dd6878b9b": ("是", "P1", "采纳 Codex：公共 swapoff 用 pte_same() 按原始位比较交换项，默认架构编码里除 soft-dirty 外没有别的附加位；x86 的 _PAGE_SWP_UFFD_WP 使比较失败。属于“把非 present 项的架构编码当成透明”。"),
    "bd1f2b2ace84": ("是", "P1", "采纳 Codex，我原判错：对 device-exclusive（非 present）项调 pte_dirty/pte_write，x86 交换项软脏位复用 _PAGE_RW，arm64 注明这些函数只对 present 项有定义。我当时只看了提交说明。"),
    "3faa3ebc89c1": ("是", "P1", "采纳 Codex，我原判错：对 device-exclusive 项清 young 位；arm64 的 PTE_AF（第 10 位）与交换类型位（6～10）重叠。"),
    "65529295607f": ("是", "P1", "采纳 Codex，我原判错：try_to_unmap_one 对 device-exclusive 项调 pte_pfn/pte_dirty/pte_soft_dirty。"),
    "ad1ac596e8a8": ("是", "P4", "采纳 Codex（我原判说不清）：Codex 核实父版本 HIGHPTE 下 pte_unmap() 实际调 kunmap_atomic()，公共层默认它对 hugetlb 指针无害，只在 32 位 HIGHPTE 架构上出错。"),
    "dde30854bddf": ("是", "P5", "采纳 Codex（弱）：公共页表自测留下父条目，默认架构的页表分配/释放会清掉旧内容；PowerPC hash 用 slab 不逐次清零，复用后重复释放。测试代码，但依赖确实跨边界。"),
    "382e6e177bc1": ("是", "P5", "采纳 Codex：按判据范围 drivers/irqchip 属公共侧；GICv3 驱动默认 arm64 NMI 入口已把 PMR 设成只允许 NMI，实际没有。"),
    "9add2cc22de6": ("不是", None, "采纳 Codex，改我原判：提交说明写明当前开 THP 迁移的架构 flush_cache_* 都是空的，有实现的 32 位 ARM 不走这条路径，没有可达的出错架构，只是潜在的接口误用。"),
    "58661a30f1bc": ("不是", None, "采纳 Codex（我原判说不清）：修的是 riscv 自己的指令缓存刷新与 CPU 上线的衔接，看不出公共层依赖了哪项未声明的效果。"),
    "b49f700668ff": ("不是", None, "维持我原判（Codex 说不清）：特定 SoC 上的回退，提交没有说明与公共边界假设的因果。"),
    "b7d9d2e3a8ab": ("说不清", None, "口径分歧：arm64 的 __ptep_set_access_flags 刷新级别不对，Codex 判为“架构没提供公共层依赖的失效效果”（a2c），我判为架构内部实现错误。实现违反接口本身应有的语义算不算“原型里没写明的假设”，判据没定。"),
    "1665c027afb2": ("说不清", None, "口径分歧（同上）：powerpc hash 模式的 tlb_flush() 调用被误删。"),
    "835e5ac3f98e": ("说不清", None, "口径分歧（同上）：riscv Svnapot 写保护没有先清整组再刷。"),
    "410982303772": ("说不清", None, "口径分歧（同上）：arm64 大页 BBM 序列里漏了 TLB 失效；提交说明提到当初删刷新是因为“公共层后面会刷”，这一点偏向“是”，但仍按口径未定处理。"),
}


def kappa(tab, n):
    po = sum(tab[(a, a)] for a in CATS) / n
    pe = sum((sum(tab[(a, b)] for b in CATS) / n) * (sum(tab[(b, a)] for b in CATS) / n) for a in CATS)
    return round(po, 3), round((po - pe) / (1 - pe), 3)


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 3), round(c + h, 3)]


def main():
    me = json.loads((HERE / "judgement.json").read_text(encoding="utf-8"))
    cx = {x["commit"][:12]: x for x in json.loads((HERE / "codex_blind/codex_judgement.json").read_text(encoding="utf-8"))}
    cand = json.loads((HERE / "candidates.json").read_text(encoding="utf-8"))
    tab = Counter((m["verdict"], cx[m["commit"]]["verdict"]) for m in me)
    po, k = kappa(tab, len(me))
    dis = [m["commit"] for m in me if m["verdict"] != cx[m["commit"]]["verdict"]]
    assert sorted(dis) == sorted(ADJ), (sorted(set(dis) ^ set(ADJ)))
    rows = []
    for m in me:
        c = m["commit"]
        if c in ADJ:
            v, p, why = ADJ[c]
        else:
            v, p, why = m["verdict"], m["pattern"], "两人一致"
        rows.append({"form": m["form"], "commit": c, "subject": m["subject"], "claude": m["verdict"], "codex": cx[c]["verdict"],
                     "final": v, "pattern": p, "adjudication": why})
    per = {}
    for f in "ABC":
        sel = [r for r in rows if r["form"] == f]
        y = sum(r["final"] == "是" for r in sel)
        N = cand["counts"][f]["after_dev_exclusion"]
        ci = wilson(y, len(sel))
        per[f] = {"yes": y, "unclear": sum(r["final"] == "说不清" for r in sel), "n": len(sel), "ratio": round(y / len(sel), 3),
                  "wilson95": ci, "est_yes": round(y / len(sel) * N, 1), "est_range": [round(ci[0] * N, 1), round(ci[1] * N, 1)]}
    pats = Counter(r["pattern"] for r in rows if r["final"] == "是")
    agreement = {"n": len(me), "raw_agreement": po, "cohen_kappa": k,
                 "table_claude_rows_codex_cols": {a: {b: tab[(a, b)] for b in CATS} for a in CATS},
                 "yes_claude": sum(m["verdict"] == "是" for m in me), "yes_codex": sum(x["verdict"] == "是" for x in cx.values()),
                 "yes_both": tab[("是", "是")], "disagreements": len(dis)}
    (HERE / "agreement.json").write_text(json.dumps(agreement, indent=1, ensure_ascii=False), encoding="utf-8")
    (HERE / "adjudication.json").write_text(json.dumps({"per_form": per, "patterns": dict(pats), "yes_total": sum(pats.values()),
                                                        "unclear_total": sum(r["final"] == "说不清" for r in rows), "rows": rows},
                                                       indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(agreement, ensure_ascii=False))
    print(json.dumps(per, ensure_ascii=False), dict(pats))


if __name__ == "__main__":
    main()
