"""Static candidates -> rule -> dynamic property checks -> attribution -> report (pipeline_v2 criteria 一, 二).

    python pipeline.py      -> report_<tree>.md, pipeline_<tree>.json   (reads existing outputs only)
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
TEMPLATES = json.loads((HERE / "templates.json").read_text(encoding="utf-8"))
TEMPLATES.pop("_note")
NAMES = {"page", "folio", "pte", "vmf", "vma", "addr"}
INTERNAL = "资源在内核内部，需要 ACTOR 或调试内核"

TREES = {
    # tree: (static output, dynamic judge json, kernel-name filter, title)
    "X1_pre": (CT / "effdep7_dev_20261113/out/X1.json", HERE / "judge_x1.json", "_pre", "X1 修复前（静态：X1 修复前的树；动态：X1 修复前内核）"),
    "X1_fix": (CT / "effdep7_dev_20261113/out/X1.json", HERE / "judge_x1.json", "_fix", "X1 修复后对照（静态同上；动态：X1 修复后内核）"),
    "CUR": (CT / "effdep7_dev_20261113/out/CUR_riscv.json", CT / "z5fix_20261115/judge_head.json", "_head", "当前版本 7.3-rc2"),
}


def rule_of(c):
    cats = set(c["skipped_cats"])
    res = set(c.get("shared_resources") or c.get("resources") or [])
    user = bool(res & NAMES)
    if "mem" in cats and user:
        return "R1"
    if cats & {"tlb", "pgtable"} and user:
        return "R2"
    if "cache" in cats:
        return "R3"
    return None


def dyn_results(path, flt):
    """{(arch_label, template): (violated_runs, valid_runs)}"""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    for k, v in d.items():
        kt, mode, t = k.split("|")
        if not kt.endswith(flt):
            continue
        arch = kt[: -len(flt)] + ("（开 MTE）" if mode == "mte" else "")
        out[(arch, t)] = (v["violated"], v["valid"])
    return out


def run(tree):
    spath, jpath, flt, title = TREES[tree]
    st = json.loads(Path(spath).read_text(encoding="utf-8"))
    dyn = dyn_results(jpath, flt)
    archs = sorted({a for a, _ in dyn})
    violated_templates = {(a, t) for (a, t), (vio, val) in dyn.items() if vio > 0}
    rows, covered_violations = [], set()
    for c in st["candidates_list"]:
        r = rule_of(c)
        row = {"fn": c["fn"], "interface": c["interface"], "loc": f"{c['file']}:{c['call_line']}", "rule": r,
               "property": c["property"], "resources": c.get("shared_resources") or c.get("resources"),
               "flag": f"{c['flag']} = {c['const']}", "skipped": c.get("same_res_calls") or c.get("skipped_all")}
        if r is None:
            row["class"], row["why"] = "manual", INTERNAL
        else:
            temps = [t for t, m in TEMPLATES.items() if m["rule"] == r and (c["fn"] in m["functions"] or c["interface"] in m["functions"])]
            row["templates"] = temps
            if not temps:
                row["class"], row["why"] = "manual", f"规则 {r} 对上了，但现有模板走不到 `{c['fn']}` 或 `{c['interface']}`"
            else:
                per = {}
                for a in archs:
                    hit = [t for t in temps if (a, t) in violated_templates]
                    per[a] = hit
                    for t in hit:
                        covered_violations.add((a, t))
                row["per_arch"] = per
                row["class"] = "confirmed" if any(per.values()) else "passed"
        rows.append(row)
    orphan = sorted(v for v in violated_templates if v not in covered_violations)
    res = {"tree": tree, "title": title, "archs": archs, "candidates": rows, "orphan_violations": orphan,
           "counts": {k: sum(1 for r in rows if r["class"] == k) for k in ("confirmed", "passed", "manual")}}
    (HERE / f"pipeline_{tree}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    L = [f"# 流水线报告：{title}", "",
         f"静态候选 {len(rows)} 个：动态确认 {res['counts']['confirmed']}，动态检查通过 {res['counts']['passed']}，"
         f"转人工 {res['counts']['manual']}；模板违反却无对应候选 {len(orphan)} 项。动态检查的架构：{'、'.join(archs)}。", ""]
    L += ["## 一、动态确认", ""]
    for r in rows:
        if r["class"] == "confirmed":
            bad = [a for a, h in r["per_arch"].items() if h]
            ok = [a for a, h in r["per_arch"].items() if not h]
            L += [f"- `{r['fn']}` 调用 `{r['interface']}`（{r['loc']}），规则 {r['rule']}",
                  f"  - 依赖性质：`{'、'.join(r['resources'])}` 在被使用或发布之前必须{r['property']}；公共层在调用后把 `{r['flag']}`，跳过了 {'、'.join('`' + x + '`' for x in r['skipped'])}",
                  f"  - 违反的架构：{'；'.join(a + '（' + '、'.join(r['per_arch'][a]) + '）' for a in bad)}",
                  f"  - 性质成立的架构：{'、'.join(ok) or '无'}"]
    if not res["counts"]["confirmed"]:
        L.append("（无）")
    L += ["", "## 二、动态检查通过（所有架构上性质都成立）", ""]
    for r in rows:
        if r["class"] == "passed":
            L.append(f"- `{r['fn']}` 调用 `{r['interface']}`（{r['loc']}），规则 {r['rule']}，由 {'、'.join(r['templates'])} 检查")
    if not res["counts"]["passed"]:
        L.append("（无）")
    L += ["", "## 三、无法动态检查，转人工分析", ""]
    for r in rows:
        if r["class"] == "manual":
            L.append(f"- `{r['fn']}` 调用 `{r['interface']}`（{r['loc']}）：资源 `{'、'.join(r['resources'] or [])}`，"
                     f"性质“{r['property']}”。原因：{r['why']}")
    if not res["counts"]["manual"]:
        L.append("（无）")
    L += ["", "## 四、模板违反了，却没有对应的静态候选（静态可能漏报）", ""]
    L += [f"- {a}：{t}（{TEMPLATES[t]['desc']}）" for a, t in orphan] or ["（无）"]
    (HERE / f"report_{tree}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(tree, res["counts"], "orphan", orphan)
    for r in rows:
        if r["class"] != "manual":
            print("   ", r["class"], r["fn"], r["interface"], r.get("per_arch"))


if __name__ == "__main__":
    for t in TREES:
        if Path(TREES[t][1]).exists():
            run(t)
        else:
            print(t, "dynamic results not ready:", TREES[t][1])
