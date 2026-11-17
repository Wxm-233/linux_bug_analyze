"""kcov criteria 四、五: hand-table accuracy, pipeline with measured coverage, candidate reach, regression.

    python analyze_kcov.py      (after symbolize.py and judge.py head / x1pre)
        -> accuracy.json, pipeline_kcov_<tree>.json, report_kcov_<tree>.md, reach.json, regression.txt
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
PV2 = CT / "pipeline_v2_20261115"
TEMPLATES = json.loads((PV2 / "templates.json").read_text(encoding="utf-8"))
TEMPLATES.pop("_note")
NAMES = {"page", "folio", "pte", "vmf", "vma", "addr"}
INTERNAL = "资源在内核内部，需要 ACTOR 或调试内核"


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def rule_of(c):  # same as pipeline_v2
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


def arch_label(kt, suffix, mode):
    return kt[: -len(suffix)] + ("（开 MTE）" if mode == "mte" else "")


def coverage(tag, suffix):
    out = {}
    for k, v in load(HERE / f"coverage_{tag}.json").items():
        kt, mode, t = k.split("|")
        out[(arch_label(kt, suffix, mode), t)] = set(v["functions"])
    return out


def dyn(path, suffix):
    out = {}
    for k, v in load(path).items():
        kt, mode, t = k.split("|")
        if kt.endswith(suffix):
            out[(arch_label(kt, suffix, mode), t)] = (v["violated"], v["valid"])
    return out


def accuracy():
    res = {}
    for tag, suffix in (("head", "_head"), ("x1pre", "_x1pre")):
        cov = coverage(tag, suffix)
        archs = sorted({a for a, _ in cov})
        tot = hit = 0
        per = {}
        for t, m in TEMPLATES.items():
            for a in archs:
                fs = cov.get((a, t), set())
                got = [f for f in m["functions"] if f in fs]
                miss = [f for f in m["functions"] if f not in fs]
                tot += len(m["functions"])
                hit += len(got)
                per[f"{a}|{t}"] = {"listed": len(m["functions"]), "observed": len(got), "missing": miss, "executed_total": len(fs)}
        res[tag] = {"listed": tot, "observed": hit, "ratio": round(hit / tot, 3) if tot else None, "per": per}
    (HERE / "accuracy.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    return res


def pipeline(tree, spath, dpath, dsuffix, ctag, csuffix, title):
    st = load(spath)
    dv = dyn(dpath, dsuffix)
    cov = coverage(ctag, csuffix)
    archs = sorted({a for a, _ in dv})
    rows = []
    for c in st["candidates_list"]:
        r = rule_of(c)
        row = {"fn": c["fn"], "interface": c["interface"], "loc": f"{c['file']}:{c['call_line']}", "rule": r,
               "property": c["property"], "resources": c.get("shared_resources") or c.get("resources")}
        executed_by = sorted({t for (a, t), fs in cov.items() if c["fn"] in fs or c["interface"] in fs})
        row["executed_by_any_template"] = executed_by
        if r is None:
            row["class"], row["why"] = "manual", INTERNAL
        else:
            per = {}
            for a in archs:
                temps = [t for t, m in TEMPLATES.items() if m["rule"] == r
                         and (c["fn"] in cov.get((a, t), set()) or c["interface"] in cov.get((a, t), set()))]
                per[a] = {"checked_by": temps, "violated": [t for t in temps if dv.get((a, t), (0, 0))[0] > 0]}
            row["per_arch"] = per
            if any(p["violated"] for p in per.values()):
                row["class"] = "confirmed"
            elif all(p["checked_by"] for p in per.values()):
                row["class"] = "passed"
            elif any(p["checked_by"] for p in per.values()):
                row["class"] = "partly_checked"
            else:
                row["class"], row["why"] = "manual", f"规则 {r} 对上了，但没有任何模板实际执行到 `{c['fn']}` 或 `{c['interface']}`"
        rows.append(row)
    viol = {(a, t) for (a, t), (v, n) in dv.items() if v > 0}
    covered = set()
    for row in rows:
        for a, p in (row.get("per_arch") or {}).items():
            for t in p["violated"]:
                covered.add((a, t))
    orphan = sorted(viol - covered)
    counts = {k: sum(1 for x in rows if x["class"] == k) for k in ("confirmed", "passed", "partly_checked", "manual")}
    res = {"tree": tree, "title": title, "archs": archs, "counts": counts, "candidates": rows, "orphan_violations": orphan}
    (HERE / f"pipeline_kcov_{tree}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    L = [f"# 流水线报告（实测覆盖）：{title}", "",
         f"静态候选 {len(rows)} 个：动态确认 {counts['confirmed']}，测过没事 {counts['passed']}，部分架构测到 {counts['partly_checked']}，"
         f"转人工 {counts['manual']}；模板违反却无对应候选 {len(orphan)} 项。", ""]
    names = {"confirmed": "一、动态确认", "passed": "二、测过没事（所有架构都有模板实际执行到，性质都成立）",
             "partly_checked": "三、只在部分架构上测到", "manual": "四、转人工"}
    for k, h in names.items():
        L += [f"## {h}", ""]
        sel = [x for x in rows if x["class"] == k]
        for x in sel:
            s = f"- `{x['fn']}` 调用 `{x['interface']}`（{x['loc']}），规则 {x['rule'] or '无'}"
            if x.get("per_arch"):
                s += "；" + "；".join(f"{a}：执行到它的模板 {'、'.join(p['checked_by']) or '无'}"
                                     + (f"，违反 {'、'.join(p['violated'])}" if p["violated"] else "") for a, p in x["per_arch"].items())
            if x.get("why"):
                s += f"；{x['why']}"
            if k == "manual" and x["executed_by_any_template"]:
                s += f"（另：被模板 {'、'.join(x['executed_by_any_template'])} 执行到过，但规则不对应）"
            L.append(s)
        L += (["（无）"] if not sel else []) + [""]
    L += ["## 五、模板违反却没有对应的静态候选", ""] + ([f"- {a}：{t}" for a, t in orphan] or ["（无）"])
    (HERE / f"report_kcov_{tree}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return res


def reach():
    cov = coverage("head", "_head")
    allfs = set().union(*cov.values()) if cov else set()
    res = {}
    for name, p in (("effdep5_32", CT / "effdep5_dev_20261113/out/CUR_riscv.json"),
                    ("effdep7_6", CT / "effdep7_dev_20261113/out/CUR_riscv.json")):
        cl = load(p)["candidates_list"]
        rows = [{"fn": c["fn"], "interface": c["interface"], "fn_executed": c["fn"] in allfs,
                 "interface_executed": c["interface"] in allfs} for c in cl]
        res[name] = {"candidates": len(rows), "fn_executed": sum(r["fn_executed"] for r in rows),
                     "fn_or_interface_executed": sum(r["fn_executed"] or r["interface_executed"] for r in rows), "rows": rows}
    (HERE / "reach.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    return res


def regression():
    L = []
    for name, new, newsuf, old, oldsuf in (
            ("当前版本", HERE / "judge_head.json", "_head", CT / "z5fix_20261115/judge_head.json", "_head"),
            ("X1 修复前", HERE / "judge_x1pre.json", "_x1pre", PV2 / "judge_x1.json", "_pre")):
        a, b = dyn(new, newsuf), dyn(old, oldsuf)
        diff = []
        for k in sorted(set(a) | set(b)):
            va = a.get(k, (None, None))[0]
            vb = b.get(k, (None, None))[0]
            if k in a and k in b and bool(va) != bool(vb):
                diff.append((k, va, vb))
        viol = sorted(f"{x[0]}:{x[1]}" for x, v in a.items() if v[0] > 0)
        L.append(f"{name}：KCOV 内核上违反的（架构:模板）{viol or '无'}；与之前不一致 {len(diff)} 项 {diff}")
    (HERE / "regression.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    return L


def main():
    acc = accuracy()
    for tag, v in acc.items():
        print("accuracy", tag, v["observed"], "/", v["listed"], v["ratio"])
    st7 = CT / "effdep7_dev_20261113/out"
    for args in (("X1_pre", st7 / "X1.json", PV2 / "judge_x1.json", "_pre", "x1pre", "_x1pre", "X1 修复前（覆盖：X1 修复前 KCOV 内核）"),
                 ("X1_fix", st7 / "X1.json", PV2 / "judge_x1.json", "_fix", "x1pre", "_x1pre", "X1 修复后对照（判错：修复后内核；覆盖：沿用修复前 KCOV 内核）"),
                 ("CUR", st7 / "CUR_riscv.json", HERE / "judge_head.json", "_head", "head", "_head", "当前版本（KCOV 内核）")):
        r = pipeline(*args)
        print("pipeline", r["tree"], r["counts"], "orphan", r["orphan_violations"])
    for k, v in reach().items():
        print("reach", k, v["fn_executed"], "/", v["candidates"], "fn or interface", v["fn_or_interface_executed"])
    for line in regression():
        print(line)


if __name__ == "__main__":
    main()
