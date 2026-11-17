"""r4 criteria 五/六: negative / positive / coverage checks and the current-version pipeline with R4.

    python analyze_r4.py      (after: python judge.py neg|pos|kcov ; symbolize_inline.py kcov in WSL)
        -> checks.md, static_rules.json, pipeline_kcov_CUR.json, report_kcov_CUR.md
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "kcov_20261115"))
import analyze_kcov as A  # noqa: E402

OLD_RULE = A.rule_of
PTEW = {"set_pte", "set_ptes", "set_pte_at", "pte_clear", "set_pmd", "set_pmd_at", "pmd_clear"}
P_HAND = ["move_ptes", "move_page_tables", "move_vma"]


def r4_rule(c):  # criteria 五.1: R4 first, otherwise the original rule_of (not rulemap2's loosened names)
    skipped = c.get("same_res_calls") or c.get("skipped_all") or []
    if any(s in PTEW for s in skipped):
        return "R4"
    return OLD_RULE(c)


def load(n):
    return json.loads((HERE / n).read_text(encoding="utf-8"))


def checks():
    neg, pos, cov = load("judge_neg.json"), load("judge_pos.json"), load("coverage_kcov.json")
    z5 = json.loads((CT / "z5fix_20261115/judge_head.json").read_text(encoding="utf-8"))
    L = ["# R4 检查结果", "", "## 阴性对照（HEAD，不开 KCOV）", ""]
    ok_neg = True
    for k in sorted(neg):
        kt, mode, t = k.split("|")
        v = neg[k]
        if t in ("P1", "P2"):
            good = v["violated"] == 0 and v["valid"] == 3
            ok_neg &= good
            L.append(f"- {kt} {t}：违反 {v['violated']}/{v['valid']} 次有效（共 {v['runs']} 次）{'' if good else '  ← 未达'}")
    diff = [k for k in z5 if k in neg and bool(z5[k]["violated"]) != bool(neg[k]["violated"])]
    missing = [k for k in z5 if k not in neg]
    other_viol = sorted(k for k, v in neg.items() if v["violated"] and k.split("|")[2] not in ("P1", "P2"))
    L += ["", f"原有 13 个模板与 z5fix 不一致 {len(diff)} 项 {diff}；缺失 {missing}；违反 {other_viol or '无'}。", "",
          "## 阳性（变异内核）", ""]
    ok_pos = True
    for kt in sorted({k.split("|")[0] for k in pos}):
        for t in ("P1", "P2"):
            v = pos.get(f"{kt}|plain|{t}", {"violated": 0, "valid": 0, "runs": 0})
            good = v["violated"] >= 2
            ok_pos &= good
            L.append(f"- {kt} {t}：违反 {v['violated']}/{v['valid']} 次有效（共 {v['runs']} 次）{'' if good else '  ← 未达'}")
        others = sorted(f"{k.split('|')[2]}={pos[k]['violated']}/{pos[k]['valid']}" for k in pos
                        if k.startswith(kt + "|") and k.split("|")[2] not in ("P1", "P2") and (pos[k]["violated"] or pos[k]["valid"] < pos[k]["runs"]))
        L.append(f"  - 其他模板违反或无效：{', '.join(others) or '无'}")
    L += ["", "## 覆盖（kcov_pa 当前版本 KCOV 内核）", ""]
    ok_cov = True
    for kt in ("riscv_head", "x86_64_head", "arm64_head"):
        for t in ("P1", "P2"):
            fs = set(cov.get(f"{kt}|plain|{t}", {}).get("functions", []))
            hit = "move_ptes" in fs
            ok_cov &= hit
            L.append(f"- {kt} {t}：move_ptes {'执行到' if hit else '没执行到'}；move_page_tables {'是' if 'move_page_tables' in fs else '否'}；"
                     f"move_normal_pmd {'是' if 'move_normal_pmd' in fs else '否'}；函数数 {len(fs)}")
    L += ["", f"汇总：阴性 {'达到' if ok_neg else '未达'}；阳性 {'达到' if ok_pos else '未达'}；覆盖 {'达到' if ok_cov else '未达'}。"]
    return L


def static():
    res = {}
    for p in sorted((CT / "effdep7_dev_20261113/out").glob("*.json")):
        rows = []
        for c in A.load(p)["candidates_list"]:
            a, b = OLD_RULE(c), r4_rule(c)
            if a != b:
                rows.append({"fn": c["fn"], "interface": c["interface"], "loc": f"{c['file']}:{c['call_line']}", "old": a, "new": b,
                             "skipped": c.get("same_res_calls") or c.get("skipped_all")})
        res[p.stem] = rows
    (HERE / "static_rules.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    return res


def pipeline():
    A.HERE = HERE
    A.TEMPLATES["P1"] = {"rule": "R4", "functions": P_HAND}
    A.TEMPLATES["P2"] = {"rule": "R4", "functions": P_HAND}
    A.rule_of = r4_rule
    r = A.pipeline("CUR", CT / "effdep7_dev_20261113/out/CUR_riscv.json", HERE / "judge_neg.json", "_head", "kcov", "_head",
                   "当前版本（规则加 R4；覆盖：本轮 KCOV；判错：本轮阴性对照）")
    A.rule_of = OLD_RULE
    return r


def main():
    L = checks()
    st = static()
    L += ["", "## 新映射下规则变化的候选（effdep7 全部 13 棵树）", ""]
    for tree, rows in st.items():
        for x in rows:
            L.append(f"- {tree}：`{x['fn']}` / `{x['interface']}`（{x['loc']}）：{x['old']} → {x['new']}；跳过的调用 {x['skipped']}")
    r = pipeline()
    L += ["", "## 当前版本流水线", "", f"计数：{r['counts']}；模板违反却无候选：{r['orphan_violations']}", ""]
    for x in r["candidates"]:
        if x.get("per_arch"):
            L.append(f"- `{x['fn']}` / `{x['interface']}` → {x['class']}，规则 {x['rule']}；"
                     + "；".join(f"{a}：{'、'.join(p['checked_by']) or '无'}" + (f"，违反 {'、'.join(p['violated'])}" if p["violated"] else "")
                                for a, p in x["per_arch"].items()))
    (HERE / "checks.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
