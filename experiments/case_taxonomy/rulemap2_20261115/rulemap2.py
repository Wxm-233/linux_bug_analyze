"""rulemap2 criteria 二/三: looser resource-name matching for rule_of; static counts and pipeline rerun.

    python rulemap2.py
        -> static_counts.json, newly_mapped.json, pipeline_kcov_<tree>.json, report_kcov_<tree>.md, compare.md
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "kcov_20261115"))
import analyze_kcov as A  # noqa: E402

OLD_RULE = A.rule_of
KPA = CT / "kcov_pa_20261115"
FAMILIES = {"page", "pages", "folio", "folios", "pfn",
            "pte", "ptes", "pmd", "pud", "p4d", "pgd",
            "addr", "address", "vaddr", "haddr", "uaddr", "vma", "vmf", "mm"}
PTRSUFFIX = {"ptep", "pmdp", "pudp", "p4dp", "pgdp"}


def user_res(name):
    toks = [t for t in name.lower().split("_") if t]
    toks = [t[:-1] if t in PTRSUFFIX else t for t in toks]
    return any(t in FAMILIES for t in toks)


def new_rule(c):  # same structure as analyze_kcov.rule_of; only the resource test changes
    cats = set(c["skipped_cats"])
    res = c.get("shared_resources") or c.get("resources") or []
    user = any(user_res(r) for r in res)
    if "mem" in cats and user:
        return "R1"
    if cats & {"tlb", "pgtable"} and user:
        return "R2"
    if "cache" in cats:
        return "R3"
    return None


def kpa_coverage(tag, suffix):
    out = {}
    for k, v in A.load(KPA / f"coverage_{tag}.json").items():
        kt, mode, t = k.split("|")
        out[(A.arch_label(kt, suffix, mode), t)] = set(v["functions"])
    return out


def static():
    files = sorted((CT / "effdep7_dev_20261113/out").glob("*.json")) + [CT / "effdep5_dev_20261113/out/CUR_riscv.json"]
    counts, newly = {}, []
    for p in files:
        name = ("effdep5/" if "effdep5" in str(p) else "effdep7/") + p.stem
        cl = A.load(p)["candidates_list"]
        o = [OLD_RULE(c) for c in cl]
        n = [new_rule(c) for c in cl]
        counts[name] = {"candidates": len(cl), "old": {r: o.count(r) for r in ("R1", "R2", "R3", None) if o.count(r)},
                        "new": {r: n.count(r) for r in ("R1", "R2", "R3", None) if n.count(r)}}
        for c, a, b in zip(cl, o, n):
            if a != b:
                newly.append({"tree": name, "fn": c["fn"], "interface": c["interface"], "loc": f"{c['file']}:{c['call_line']}",
                              "old": a, "new": b, "resources": c.get("shared_resources") or c.get("resources"),
                              "skipped_cats": c["skipped_cats"], "flag": f"{c['flag']} = {c['const']}",
                              "skipped": c.get("same_res_calls") or c.get("skipped_all"), "property": c["property"]})
    (HERE / "static_counts.json").write_text(json.dumps({str(k): v for k, v in counts.items()}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (HERE / "newly_mapped.json").write_text(json.dumps(newly, indent=1, ensure_ascii=False), encoding="utf-8")
    return counts, newly


def pipelines():
    A.HERE = HERE
    A.coverage = kpa_coverage
    st7 = CT / "effdep7_dev_20261113/out"
    trees = (("X1_pre", st7 / "X1.json", A.PV2 / "judge_x1.json", "_pre", "x1pre", "_x1pre", "X1 修复前"),
             ("X1_fix", st7 / "X1.json", A.PV2 / "judge_x1.json", "_fix", "x1pre", "_x1pre", "X1 修复后"),
             ("CUR", st7 / "CUR_riscv.json", CT / "z5fix_20261115/judge_head.json", "_head", "head", "_head", "当前版本"))
    res = {}
    for label, rule in (("old", OLD_RULE), ("new", new_rule)):
        A.rule_of = rule
        for t in trees:
            r = A.pipeline(*t)
            if label == "old":  # keep only the new-mapping files on disk
                (HERE / f"pipeline_kcov_{t[0]}.json").unlink()
                (HERE / f"report_kcov_{t[0]}.md").unlink()
            res[(label, t[0])] = r
    A.rule_of = OLD_RULE
    return res


def main():
    counts, newly = static()
    for k, v in counts.items():
        if v["old"] != v["new"]:
            print("static", k, v)
    print("newly mapped", len(newly))
    for x in newly:
        print(" ", x["tree"], x["fn"], x["interface"], x["loc"], x["old"], "->", x["new"], x["resources"], x["skipped_cats"])
    res = pipelines()
    L = ["# 新旧映射下的流水线（覆盖：kcov_pa 实测；判错：不开 KCOV 的内核）", "",
         "| 树 | 映射 | 动态确认 | 测过没事 | 部分架构测到 | 转人工 | 模板违反却无候选 |", "|---|---|---|---|---|---|---|"]
    for (label, tree), r in res.items():
        c = r["counts"]
        L.append(f"| {tree} | {'旧' if label == 'old' else '新'} | {c['confirmed']} | {c['passed']} | {c['partly_checked']} | {c['manual']} | {len(r['orphan_violations'])} |")
        print("pipeline", label, tree, c, "orphan", r["orphan_violations"])
    L.append("")
    for tree in ("X1_pre", "X1_fix", "CUR"):
        old = {(x["fn"], x["interface"], x["loc"]): x["class"] for x in res[("old", tree)]["candidates"]}
        for x in res[("new", tree)]["candidates"]:
            k = (x["fn"], x["interface"], x["loc"])
            if old[k] != x["class"]:
                L.append(f"- {tree}：`{x['fn']}` / `{x['interface']}`（{x['loc']}）：{old[k]} → {x['class']}，规则 {x['rule']}；"
                         + "；".join(f"{a}：{'、'.join(p['checked_by']) or '无'}" for a, p in (x.get("per_arch") or {}).items()))
    (HERE / "compare.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
