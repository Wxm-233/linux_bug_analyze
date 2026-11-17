"""Supplementary analysis written AFTER seeing the criteria results (not a replacement for them).

KCOV cannot see a function that is inlined (no own symbol) or defined in a file built with
KCOV_INSTRUMENT := n. The criteria pipeline treats such a function as "not executed". Here:
  1. reach: each candidate function is executed / observable but not executed / not observable.
  2. hybrid attribution: per architecture, if neither the candidate's function nor its interface is
     observable there, fall back to the hand table (templates.json) for that architecture; otherwise
     use measured coverage as in the criteria pipeline.

    python supplement.py   -> supplement.json, supplement.md
"""
import json
from pathlib import Path

import analyze_kcov as A
from classify_missing import ARCHDIR, not_instrumented

HERE = Path(__file__).resolve().parent


def load_info(name):
    info = {}
    for line in (HERE / name).read_text(encoding="utf-8").splitlines():
        f, nm, defs = line.split("|")
        info[f] = (set(nm.split()), [d for d in defs.split(",") if d])
    return info


INFO = {**load_info("funcinfo.txt"), **load_info("candinfo.txt")}
NOTINS = {"head": not_instrumented("HEAD"), "x1pre": not_instrumented("x1pre")}


def observable(f, arch, tag):
    base = arch.replace("（开 MTE）", "")
    nm, defs = INFO.get(f, (set(), []))
    if f"{base}_{tag}" not in nm:
        return False
    files, dirs = NOTINS[tag]
    cand = [d for d in defs if d.startswith(ARCHDIR[base])] or [d for d in defs if not d.startswith("arch/")]
    return not (cand and all(d in files or any(d.startswith(x) for x in dirs) for d in cand))


def reach():
    cov = A.coverage("head", "_head")
    archs = sorted({a for a, _ in cov})
    allfs = set().union(*cov.values())
    out = {}
    for name, p in (("effdep5_32", A.CT / "effdep5_dev_20261113/out/CUR_riscv.json"),
                    ("effdep7_6", A.CT / "effdep7_dev_20261113/out/CUR_riscv.json")):
        rows = []
        for c in A.load(p)["candidates_list"]:
            f = c["fn"]
            obs = [a for a in archs if observable(f, a, "head")]
            st = "executed" if f in allfs else ("observable_not_executed" if obs else "not_observable")
            rows.append({"fn": f, "interface": c["interface"], "status": st, "observable_on": obs})
        out[name] = {"candidates": len(rows), **{k: sum(r["status"] == k for r in rows)
                                                  for k in ("executed", "observable_not_executed", "not_observable")},
                     "rows": rows}
    return out


def hybrid(tree, spath, dpath, dsuffix, ctag, csuffix, title):
    st, dv, cov = A.load(spath), A.dyn(dpath, dsuffix), A.coverage(ctag, csuffix)
    archs = sorted({a for a, _ in dv})
    rows = []
    for c in st["candidates_list"]:
        r = A.rule_of(c)
        row = {"fn": c["fn"], "interface": c["interface"], "rule": r}
        if r is None:
            row["class"] = "manual"
            rows.append(row)
            continue
        per = {}
        for a in archs:
            vis = observable(c["fn"], a, ctag) or observable(c["interface"], a, ctag)
            if vis:
                temps = [t for t, m in A.TEMPLATES.items() if m["rule"] == r
                         and (c["fn"] in cov.get((a, t), set()) or c["interface"] in cov.get((a, t), set()))]
                src = "实测"
            else:
                temps = [t for t, m in A.TEMPLATES.items() if m["rule"] == r
                         and (c["fn"] in m["functions"] or c["interface"] in m["functions"])]
                src = "手写表兜底"
            per[a] = {"source": src, "checked_by": temps, "violated": [t for t in temps if dv.get((a, t), (0, 0))[0] > 0]}
        row["per_arch"] = per
        if any(p["violated"] for p in per.values()):
            row["class"] = "confirmed"
        elif all(p["checked_by"] for p in per.values()):
            row["class"] = "passed"
        elif any(p["checked_by"] for p in per.values()):
            row["class"] = "partly_checked"
        else:
            row["class"] = "manual"
        rows.append(row)
    viol = {(a, t) for (a, t), (v, n) in dv.items() if v > 0}
    covered = {(a, t) for row in rows for a, p in (row.get("per_arch") or {}).items() for t in p["violated"]}
    return {"tree": tree, "title": title, "counts": {k: sum(x["class"] == k for x in rows)
                                                      for k in ("confirmed", "passed", "partly_checked", "manual")},
            "candidates": rows, "orphan_violations": sorted(viol - covered)}


def main():
    st7 = A.CT / "effdep7_dev_20261113/out"
    trees = [hybrid(*a) for a in (
        ("X1_pre", st7 / "X1.json", A.PV2 / "judge_x1.json", "_pre", "x1pre", "_x1pre", "X1 修复前"),
        ("X1_fix", st7 / "X1.json", A.PV2 / "judge_x1.json", "_fix", "x1pre", "_x1pre", "X1 修复后"),
        ("CUR", st7 / "CUR_riscv.json", HERE / "judge_head.json", "_head", "head", "_head", "当前版本"))]
    rc = reach()
    (HERE / "supplement.json").write_text(json.dumps({"hybrid": trees, "reach": rc}, indent=1, ensure_ascii=False), encoding="utf-8")
    L = ["# 事后补充分析：考虑 KCOV 盲区（不替代判据结果）", "",
         "KCOV 看不到两类函数：被内联的（没有独立符号），和定义在关掉插桩的文件里的（如 `mm/page_alloc.c`）。"
         "判据规定的流水线把它们一律当成“没执行”。这里做两件事：", "",
         "1. 混合归因：某个架构上，候选的函数和接口都看不到时，退回用手写表；看得到时用实测覆盖。",
         "2. 候选可达性分三类：执行到 / 看得到但没执行到 / 看不到。", "", "## 混合归因", "",
         "| 树 | 动态确认 | 测过没事 | 部分架构测到 | 转人工 | 模板违反却无候选 |", "|---|---|---|---|---|---|"]
    for t in trees:
        c = t["counts"]
        L.append(f"| {t['title']} | {c['confirmed']} | {c['passed']} | {c['partly_checked']} | {c['manual']} | {len(t['orphan_violations'])} |")
    L.append("")
    for t in trees:
        for row in t["candidates"]:
            if row.get("per_arch"):
                L.append(f"- {t['title']}：`{row['fn']}` / `{row['interface']}` → {row['class']}；" + "；".join(
                    f"{a}（{p['source']}）：{'、'.join(p['checked_by']) or '无'}" + (f"，违反 {'、'.join(p['violated'])}" if p["violated"] else "")
                    for a, p in row["per_arch"].items()))
    L += ["", "## 候选可达性（当前版本 KCOV 内核，四个架构配置合并）", "",
          "| 候选集 | 个数 | 执行到 | 看得到但没执行到 | 看不到 |", "|---|---|---|---|---|"]
    for k, v in rc.items():
        L.append(f"| {k} | {v['candidates']} | {v['executed']} | {v['observable_not_executed']} | {v['not_observable']} |")
    L.append("")
    for k, v in rc.items():
        L += [f"### {k}", ""] + [f"- `{r['fn']}`（接口 `{r['interface']}`）：{r['status']}" for r in v["rows"]] + [""]
    (HERE / "supplement.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    for t in trees:
        print(t["tree"], t["counts"], "orphan", t["orphan_violations"])
    for k, v in rc.items():
        print(k, {x: v[x] for x in ("candidates", "executed", "observable_not_executed", "not_observable")})


if __name__ == "__main__":
    main()
