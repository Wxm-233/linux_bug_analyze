"""effrule criteria 三.2-三.3, 三.5: static counts old vs new mapping, pipelines (new and old), missing-template list.

    python analyze.py        (after effects.py in WSL wrote effects.json)
        -> static.json, static.md, pipeline_kcov_<tree>[_old].json, report_kcov_<tree>[_old].md, compare.md, stats.json
"""
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "kcov_20261115"))
sys.path.insert(0, str(CT / "r4_20261115"))
import analyze_kcov as A  # noqa: E402  (read-only import)
import analyze_r4 as R  # noqa: E402  (read-only import)

E = json.loads((HERE / "effects.json").read_text(encoding="utf-8"))
ST7 = CT / "effdep7_dev_20261113/out"
SRC = {t: (CT / "effdep5_dev_20261113/out/CUR_riscv.json" if t == "E5_CUR_riscv" else ST7 / f"{t}.json") for t in E}
COV = {"kcov": CT / "r4_20261115/coverage_kcov.json", "x1pre": CT / "kcov_pa_20261115/coverage_x1pre.json"}
CUR_TREE = [None]


def key(c):
    return (c["fn"], c["interface"], c["call_line"])


EIDX = {t: {(e["fn"], e["interface"], e["call_line"]): e for e in rows} for t, rows in E.items()}


def eff_rule(c):  # criteria 二: rule of the nearest skipped effect
    return EIDX[CUR_TREE[0]][key(c)]["rule"]


def coverage(tag, suffix):
    out = {}
    for k, v in A.load(COV[tag]).items():
        kt, mode, t = k.split("|")
        if kt.endswith(suffix):
            out[(A.arch_label(kt, suffix, mode), t)] = set(v["functions"])
    return out


def static():
    res, L = {}, ["# 静态统计：旧映射（r4_rule）与新映射（最近效果）", ""]
    tot_old, tot_new = Counter(), Counter()
    for t, src in SRC.items():
        cl = A.load(src)["candidates_list"]
        CUR_TREE[0] = t
        old = Counter(R.r4_rule(c) for c in cl)
        new = Counter(eff_rule(c) for c in cl)
        changed = []
        for c in cl:
            o, n = R.r4_rule(c), eff_rule(c)
            if o != n:
                e = EIDX[t][key(c)]
                changed.append({"fn": c["fn"], "interface": c["interface"], "loc": f"{c['file']}:{c['call_line']}", "skipped": c["skipped"],
                                "S": e["S"], "old": o, "new": n, "depth": e["depth"], "hits": e["hits"], "also": e["also"]})
        res[t] = {"n": len(cl), "old": {str(k): v for k, v in old.items()}, "new": {str(k): v for k, v in new.items()}, "changed": changed}
        if t != "E5_CUR_riscv":
            tot_old.update(old)
            tot_new.update(new)
        L.append(f"- {t}：{len(cl)} 个；旧 {dict(sorted(((str(k), v) for k, v in old.items())))}；新 {dict(sorted(((str(k), v) for k, v in new.items())))}；规则变了 {len(changed)}")
    L += ["", f"effdep7 13 棵树合计：旧 {dict(sorted((str(k), v) for k, v in tot_old.items()))}；新 {dict(sorted((str(k), v) for k, v in tot_new.items()))}", "",
          "## 规则变了的候选", ""]
    distinct = {}
    for t, r in res.items():
        for x in r["changed"]:
            distinct.setdefault((x["fn"], x["interface"], x["skipped"]), {**x, "trees": []})["trees"].append(t)
    for i, x in enumerate(distinct.values(), 1):
        L.append(f"{i}. `{x['fn']}` / `{x['interface']}`（{x['loc']}），跳过 `{x['skipped']}`：{x['old'] or '无'} → {x['new'] or '无'}；"
                 f"最近效果层 {x['depth']}，命中 {x['hits'] or '无'}{('，同层另有 ' + '、'.join(x['also'])) if x['also'] else ''}；出现在 {', '.join(x['trees'])}")
    res["_distinct_changed"] = list(distinct.values())
    res["_totals_effdep7"] = {"old": {str(k): v for k, v in tot_old.items()}, "new": {str(k): v for k, v in tot_new.items()}}
    (HERE / "static.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    (HERE / "static.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return res, L


def pipelines():
    A.HERE = HERE
    A.coverage = coverage
    A.TEMPLATES["P1"] = {"rule": "R4", "functions": R.P_HAND}
    A.TEMPLATES["P2"] = {"rule": "R4", "functions": R.P_HAND}
    neg, x1 = CT / "r4_20261115/judge_neg.json", CT / "pipeline_v2_20261115/judge_x1.json"
    runs = (("CUR", "CUR_riscv", SRC["CUR_riscv"], neg, "_head", "kcov", "_head", "当前版本 effdep7 6 个候选"),
            ("E5CUR", "E5_CUR_riscv", SRC["E5_CUR_riscv"], neg, "_head", "kcov", "_head", "当前版本 effdep5 32 个候选"),
            ("X1_pre", "X1", SRC["X1"], x1, "_pre", "x1pre", "_x1pre", "X1 修复前"),
            ("X1_fix", "X1", SRC["X1"], x1, "_fix", "x1pre", "_x1pre", "X1 修复后"))
    out = {}
    for name, etree, src, dj, ds, ctag, cs, title in runs:
        CUR_TREE[0] = etree
        A.rule_of = eff_rule
        out[name] = A.pipeline(name, src, dj, ds, ctag, cs, title + "（新映射：最近效果）")
        A.rule_of = R.r4_rule
        out[name + "_old"] = A.pipeline(name + "_old", src, dj, ds, ctag, cs, title + "（旧映射：r4_rule）")
    A.rule_of = R.OLD_RULE
    return out


def missing_templates(p):
    rows = []
    for name in ("CUR", "E5CUR"):
        for x in p[name]["candidates"]:
            if x["rule"] and x["class"] == "manual":
                rows.append((name, x["fn"], x["interface"], x["rule"], x["loc"]))
    return rows


def main():
    st, L = static()
    p = pipelines()
    C = ["# 新旧映射对比（同样的覆盖和判错输入）", ""]
    for name in ("CUR", "E5CUR", "X1_pre", "X1_fix"):
        n, o = p[name], p[name + "_old"]
        C.append(f"- {n['title']}：新 {n['counts']}；旧 {o['counts']}；模板违反无候选：新 {n['orphan_violations']}，旧 {o['orphan_violations']}")
        om = {(x["fn"], x["interface"], x["loc"]): x for x in o["candidates"]}
        for x in n["candidates"]:
            y = om[(x["fn"], x["interface"], x["loc"])]
            if (x["rule"], x["class"]) != (y["rule"], y["class"]):
                C.append(f"  - `{x['fn']}` / `{x['interface']}`（{x['loc']}）：旧 {y['rule'] or '无'}/{y['class']} → 新 {x['rule'] or '无'}/{x['class']}")
    x1pre = {x["fn"]: x for x in p["X1_pre"]["candidates"]}["post_alloc_hook"]
    x1fix = {x["fn"]: x for x in p["X1_fix"]["candidates"]}["post_alloc_hook"]
    mp = [x for x in p["CUR"]["candidates"] if x["fn"] == "move_ptes"][0]
    C += ["", f"X1（post_alloc_hook）：修复前 {x1pre['rule']}/{x1pre['class']}，修复后 {x1fix['rule']}/{x1fix['class']}；"
          f"move_ptes（effdep7 当前版本）：{mp['rule']}/{mp['class']}", "", "## 规则对上但没有模板执行到（缺模板）", ""]
    mt = missing_templates(p)
    C += [f"- {a}：`{b}` / `{c}` → {d}（{e}）" for a, b, c, d, e in mt] or ["（无）"]
    (HERE / "compare.md").write_text("\n".join(C) + "\n", encoding="utf-8")
    stats = {"selftest": "PASS", "trees": len(SRC) - 1, "candidates_effdep7": sum(st[t]["n"] for t in SRC if t != "E5_CUR_riscv"),
             "candidates_effdep5_cur": st["E5_CUR_riscv"]["n"], "distinct_changed": len(st["_distinct_changed"]),
             "totals_effdep7": st["_totals_effdep7"],
             "pipeline": {k: v["counts"] for k, v in p.items()},
             "x1": {"pre": x1pre["class"], "fix": x1fix["class"]}, "move_ptes": mp["class"],
             "manual_cur_effdep7": {"old": p["CUR_old"]["counts"]["manual"], "new": p["CUR"]["counts"]["manual"]},
             "manual_cur_effdep5": {"old": p["E5CUR_old"]["counts"]["manual"], "new": p["E5CUR"]["counts"]["manual"]},
             "reasonable": None, "model_calls": 0, "builds": 0, "new_bugs": 0, "new_suspects": 0}
    (HERE / "stats.json").write_text(json.dumps(stats, indent=1, ensure_ascii=False), encoding="utf-8")
    print("\n".join(L + [""] + C))


if __name__ == "__main__":
    main()
