"""encrank criteria 二～四: misread table, validation against p1dyn and P1 samples, encoding-aware ranking.

    python analyze.py     -> table.json, table.md, validation.md, ranking.json, ranking.md, new_review.json
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
ENC = json.loads((HERE / "encoding.json").read_text())
ARCHS = list(ENC)
HAS_PFN = {"mig_r", "mig_re", "mig_w", "dp_r", "dp_w", "dexcl"}


def misread(level, acc, arch):
    """(misread?, list of (mod, kind)) for one accessor on one arch; None if nothing known"""
    cell = ENC[arch].get(level, {}).get(acc, {})
    hits, known = [], False
    for mod, kinds in cell.items():
        if not isinstance(kinds, dict):
            continue
        for k, v in kinds.items():
            if v == "unknown":
                continue
            known = True
            bad = (v == 0) if acc == "pfn" else (v == 1)
            if bad:
                hits.append((mod, k))
    return (bool(hits), hits) if known else (None, [])


def features(level, acc):
    M, avail, detail = [], [], {}
    for a in ARCHS:
        r, hits = misread(level, acc, a)
        if r is None:
            continue
        avail.append(a)
        if r:
            M.append(a)
            detail[a] = hits
    partial = bool(M) and len(M) < len(avail)
    return {"M": M, "avail": avail, "partial": partial, "latent": partial and "x86_64" not in M, "n": len(M), "detail": detail}


TABLE = {}
for level in ("pte", "pmd"):
    for acc in {a for arch in ARCHS for a in ENC[arch].get(level, {})}:
        TABLE[f"{level}_{acc.lower()}" if acc != "MKOLD" else f"{level}_mkold"] = features(level, acc)


def v(arch, level, acc, mod, kind):
    try:
        return ENC[arch][level][acc][mod][kind]
    except (KeyError, TypeError):
        return "n/a"


def validation():
    L = ["# 编码表核对", "", "## 与 p1dyn 实测对照", ""]
    checks = [
        ("S1 arm64 pmd_young(写迁移项)=1", v("arm64", "pmd", "young", "plain", "mig_w"), 1),
        ("S1 arm64 pmd_dirty(写迁移项)=0", v("arm64", "pmd", "dirty", "plain", "mig_w"), 0),
        ("S1 riscv pmd_young(写迁移项)=0", v("riscv", "pmd", "young", "plain", "mig_w"), 0),
        ("S1 riscv pmd_dirty(写迁移项)=1", v("riscv", "pmd", "dirty", "plain", "mig_w"), 1),
        ("S1 x86_64 pmd_young(写迁移项)=0", v("x86_64", "pmd", "young", "plain", "mig_w"), 0),
        ("S1 x86_64 pmd_dirty(写迁移项)=1", v("x86_64", "pmd", "dirty", "plain", "mig_w"), 1),
        ("S2 arm64 pte_mkold 改变 device-exclusive", v("arm64", "pte", "MKOLD", "plain", "dexcl"), 1),
        ("S2 riscv pte_young(device-exclusive)=0", v("riscv", "pte", "young", "plain", "dexcl"), 0),
        ("S2 x86_64 pte_young(device-exclusive)=0", v("x86_64", "pte", "young", "plain", "dexcl"), 0),
        ("S2 x86_64 pte_mkold 不改变 device-exclusive", v("x86_64", "pte", "MKOLD", "plain", "dexcl"), 0),
    ]
    ok1 = 0
    for name, got, want in checks:
        ok = got == want
        ok1 += ok
        L.append(f"- {name}：编码表 {got}，{'对' if ok else '**不对**'}")
    L += ["", f"合计 {ok1}/{len(checks)}（判据的 6 项实测展开为 {len(checks)} 个具体值）", "", "## P1 样本出错的架构", ""]
    samp = [
        ("26e7888a0c89 loongarch pmd_leaf 对迁移项 PMD 读成 1", any(v("loongarch", "pmd", "leaf", m, k) == 1 for m in ("plain", "sd", "uf") for k in ("mig_r", "mig_re", "mig_w")),
         {a: [k for k in ("mig_r", "mig_w", "dp_w") if v(a, "pmd", "leaf", "plain", k) == 1] for a in ARCHS}),
        ("43e7f189769c x86_64 pmd_write 对带软脏的 device-private PMD 读成 1", v("x86_64", "pmd", "write", "sd", "dp_w") == 1 or v("x86_64", "pmd", "write", "sd", "dp_r") == 1,
         {a: [v(a, "pmd", "write", "sd", "dp_r"), v(a, "pmd", "write", "plain", "dp_r")] for a in ARCHS}),
        ("bd1f2b2ace84 x86_64 pte_write 对带软脏的 device-exclusive 读成 1", v("x86_64", "pte", "write", "sd", "dexcl") == 1,
         {a: [v(a, "pte", "write", "sd", "dexcl"), v(a, "pte", "dirty", "plain", "dexcl")] for a in ARCHS}),
        ("65529295607f 同上（try_to_unmap_one 的 pte_dirty/pte_pfn）", v("x86_64", "pte", "write", "sd", "dexcl") == 1 or v("x86_64", "pte", "dirty", "sd", "dexcl") == 1,
         {a: [v(a, "pte", "dirty", "sd", "dexcl"), v(a, "pte", "pfn", "plain", "dexcl")] for a in ARCHS}),
        ("3faa3ebc89c1 arm64 pte_mkold 改变 device-exclusive", v("arm64", "pte", "MKOLD", "plain", "dexcl") == 1,
         {a: v(a, "pte", "MKOLD", "plain", "dexcl") for a in ARCHS}),
    ]
    ok2 = 0
    for name, ok, detail in samp:
        ok2 += bool(ok)
        L.append(f"- {name}：{'解释得了' if ok else '**解释不了**'}；各架构 {detail}")
    L += ["", f"合计 {ok2}/{len(samp)}"]
    (HERE / "validation.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return ok1, len(checks), ok2, len(samp)


def key_of(accs, base):
    best = None
    for a in accs:
        f = TABLE.get(a)
        k = (0, 0, 0) if not f else (int(f["latent"]), int(f["partial"]), f["n"])
        best = k if best is None or k > best else best
    best = best or (0, 0, 0)
    return (-best[0], -best[1], -best[2]) + base


def rank_contract():
    h = json.loads((CT / "contract_20261115/head.json").read_text())
    rows = []
    for i, d in enumerate(h["deviations"]):
        rows.append({**{k: d[k] for k in ("file", "line", "func", "A")}, "orig_rank": i + 1, "items": d["items"],
                     "key": key_of([d["A"]], (i,))})
    rows.sort(key=lambda r: r["key"] + (r["file"], r["line"]))
    return rows


def rank_p1():
    h = json.loads((CT / "p1check_20261115/head.json").read_text())
    om = {"O1": 0, "O2": 1, "O3": 2}
    base = sorted(h["findings"], key=lambda x: (om[x["origin"]], x["file"], x["line"]))
    rows = []
    for i, f in enumerate(base):
        rows.append({**{k: f[k] for k in ("file", "line", "func")}, "A": f["accessor"], "origin": f["origin"], "orig_rank": i + 1,
                     "key": key_of([f["accessor"]], (i,))})
    rows.sort(key=lambda r: r["key"] + (r["file"], r["line"]))
    return rows


def pos(rows, f, line):
    return next((i for i, r in enumerate(rows, 1) if r["file"] == f and r["line"] == line), None)


def main():
    ok1, n1, ok2, n2 = validation()
    tbl = {a: {k: v for k, v in f.items() if k != "detail"} for a, f in TABLE.items()}
    (HERE / "table.json").write_text(json.dumps({"archs": ARCHS, "table": TABLE}, indent=1), encoding="utf-8")
    L = ["# 受限接口的跨架构读错表", "", "| 接口 | 可用架构 | 读错的架构 | 部分读错 | 潜伏（x86 不读错） |", "|---|---|---|---|---|"]
    for a in sorted(tbl):
        t = tbl[a]
        L.append(f"| `{a}` | {len(t['avail'])} | {', '.join(t['M']) or '—'} | {'是' if t['partial'] else ''} | {'是' if t['latent'] else ''} |")
    (HERE / "table.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    rc, rp = rank_contract(), rank_p1()
    B = [("fs/proc/task_mmu.c", 1129, "B-1"), ("include/linux/pgtable.h", 534, "B-2")]
    res = {"validation": {"p1dyn": [ok1, n1], "samples": [ok2, n2]},
           "contract": {b: {"new": pos(rc, f, l), "old": next((r["orig_rank"] for r in rc if r["file"] == f and r["line"] == l), None)} for f, l, b in B},
           "p1": {b: {"new": pos(rp, f, l), "old": next((r["orig_rank"] for r in rp if r["file"] == f and r["line"] == l), None)} for f, l, b in B},
           "n": {"contract": len(rc), "p1": len(rp)}}
    reviewed = set()
    for x in json.loads((CT / "p1check_20261115/o1_adjudication.json").read_text(encoding="utf-8"))["rows"]:
        f, l = x["loc"].rsplit(":", 1)
        reviewed.add((f, int(l)))
    for x in json.loads((CT / "contract_20261115/top30.json").read_text(encoding="utf-8")):
        reviewed.add((x["file"], x["line"]))
    merged, seen = [], set()
    for r in rc[:30] + rp[:30]:
        k = (r["file"], r["line"])
        if k in seen:
            continue
        seen.add(k)
        merged.append({**{x: r[x] for x in ("file", "line", "func", "A")}, "reviewed_before": k in reviewed,
                       "M": TABLE.get(r["A"], {}).get("M", [])})
    new = [m for m in merged if not m["reviewed_before"]]
    res["new_top"] = {"merged": len(merged), "already_reviewed": len(merged) - len(new), "to_review": len(new)}
    (HERE / "ranking.json").write_text(json.dumps({**res, "contract_top30": [{k: r[k] for k in ("file", "line", "func", "A", "orig_rank")} for r in rc[:30]],
                                                   "p1_top30": [{k: r[k] for k in ("file", "line", "func", "A", "orig_rank")} for r in rp[:30]]},
                                                  indent=1, ensure_ascii=False), encoding="utf-8")
    (HERE / "new_review.json").write_text(json.dumps(new, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print(open(HERE / "validation.md", encoding="utf-8").read())
    print(open(HERE / "table.md", encoding="utf-8").read())


if __name__ == "__main__":
    main()
