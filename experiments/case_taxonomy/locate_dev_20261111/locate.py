"""Localisation report (locate criteria 二、三). Pure Python, read-only.

    python locate.py   -> report/<group>.md, results.json   (data: fieldhint2_dev_20261111, index/<group>.json)
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
RD = CT / "fieldhint2_dev_20261111"
SAMPLES = ["A101", "A310", "A171", "A181", "B467"]
CLASS = {"type": "类型一致性检查", "impl": "实现一致性检查", None: "不归类"}
sys.path.insert(0, str(CT / "difftest_tools_20261111"))
import importlib.util  # noqa: E402
_s = importlib.util.spec_from_file_location("tools_score", CT / "difftest_tools_20261111" / "score.py")
SC = importlib.util.module_from_spec(_s)
_s.loader.exec_module(SC)


def tok_matches(arg, hint):
    if hint.startswith("o:"):
        m = re.match(r"o:[zag]:(\d+)$", arg)
        return bool(m) and m.group(1) == hint[2:]
    return arg == hint


def candidates(case, idx, probes, kernels):
    """criteria 二: ordered list of candidates for one logical case"""
    out = []
    sc = case["sc"]
    if "rel" in case:
        tsm = idx["macro_values"].get("TASK_SIZE_MAX", {})
        pk = {k: {x: probes[k]["values"].get(x) for x in ("uaccess_top", "mmap_top")} for k in kernels if k in probes}
        selfc = [k for k, v in pk.items() if v["uaccess_top"] and v["mmap_top"]
                 and int(v["uaccess_top"], 16) not in (int(v["mmap_top"], 16), int(v["mmap_top"], 16) + 1)]
        out.append({"kind": "limit", "what": "用户地址上限（相对上限提示值）", "items": ["TASK_SIZE_MAX"],
                    "static_values": tsm, "probes": pk, "self_inconsistent": selfc, "class": "type"})
    if "fvar" in case:
        m = case["fvar"]["field"]
        fns = idx["fields"].get(m, [])
        out.append({"kind": "field", "what": f"结构体字段 {m}，改为 0x{case['fvar']['value']}（{case['fvar']['cat']}）",
                    "items": [m], "compared_in": fns[:8],
                    "class": "impl" if any(f[3] for f in fns) else "type"})
    if sc == "raw_nr":
        ifs = (idx.get("raw_nr") or {}).get("ifs", [])
        out.append({"kind": "nr", "what": "系统调用号的检查", "items": ["raw_nr"] + [x["fn"] for x in ifs],
                    "where": ifs, "static_values": idx["macro_values"].get("NR_syscalls"), "class": "type"})
    hits = []
    for s in idx["sites"].get(sc, []):
        ps = [int(p) for p, vs in s["values"].items()
              if int(p) < len(case["args"]) and any(tok_matches(case["args"][int(p)], v) for v in vs)]
        if ps:
            hits.append((s, ps))
    for s, ps in sorted(hits, key=lambda x: -x[0]["score"])[:5]:
        cls = "type" if s["e"] == 3 else "impl" if s["e"] == 2 else None
        out.append({"kind": "site", "what": f"{s['fn']}（{s['file']}:{s['line']}），参数 {ps} 的值与提示吻合",
                    "items": [s["fn"], s["e_item"]] + s["items"], "e_item": s["e_item"], "e": s["e"],
                    "score": s["score"], "static_values": idx["macro_values"].get(s["e_item"]), "class": cls})
    return out


HITS = {"A101": lambda c: "arch_get_mmap_end" in c["items"],
        "A171": lambda c: c["kind"] == "limit" or "TASK_SIZE_MAX" in c["items"],
        "A181": lambda c: bool({"__put_user", "put_user"} & set(c["items"])),
        "A310": lambda c: c["kind"] == "nr",
        "B467": lambda c: any(f[1].startswith("drivers/perf/riscv_pmu") for f in c.get("compared_in", []))
        or any(isinstance(x, str) and x.startswith("riscv_pmu") for x in c["items"])}


def text(c):
    s = f"- **{CLASS[c['class']]}**：{c['what']}"
    if c.get("e_item"):
        s += f"；边界项 `{c['e_item']}`，证据 {c['e']}，得分 {c['score']}"
    if c.get("static_values"):
        s += "；静态取值 " + "、".join(f"{a}={v if not isinstance(v, int) else hex(v)}" for a, v in c["static_values"].items())
    if c.get("probes"):
        s += "；探测 " + "、".join(f"{k}: 指针检查上限 0x{v['uaccess_top']}，可映射最高 0x{v['mmap_top']}"
                                for k, v in c["probes"].items())
    if c.get("self_inconsistent"):
        s += f"；**同架构自洽问题**：{', '.join(c['self_inconsistent'])} 两个上限对不上"
    if c.get("compared_in"):
        s += "；比较位置 " + "、".join(f"{f[0]}（{f[1]}:{f[2]}{'，架构代码' if f[3] else ''}）" for f in c["compared_in"][:4])
    return s


def main():
    probes = json.loads((CT / "rtprobe_dev_20261110" / "probes.json").read_text())
    res = {"samples": {}, "current": {}}
    (HERE / "report").mkdir(exist_ok=True)
    for g in SAMPLES + ["CUR"]:
        idx = json.loads((HERE / "index" / f"{g}.json").read_text())
        cases = {str(c["id"]): c for c in json.loads((RD / "run" / g / "cases.json").read_text())["cases"]}
        cmp_ = json.loads((RD / "cmp" / g / "compare.json").read_text(encoding="utf8"))
        kernels = list(cmp_["kernels"])
        lines = [f"# 定位报告：{g}", ""]
        if g != "CUR":
            conf = SC.read_json(RD / "confirm.json").get(g, {})
            det = sorted(SC.detecting(cmp_, f"{g.lower()}_pre", f"{g.lower()}_fix"), key=int)
            rows = []
            for i in det:
                if not conf.get(i, {}).get("ok"):
                    continue
                cs = candidates(cases[i], idx, probes, kernels)
                rows.append({"id": i, "sc": cases[i]["sc"], "n": len(cs), "top_hit": bool(cs) and HITS[g](cs[0]),
                             "any_hit": any(HITS[g](c) for c in cs), "candidates": cs})
            res["samples"][g] = {"detecting_confirmed": len(rows), "with_candidate": sum(1 for r in rows if r["n"]),
                                 "top_hit": sum(r["top_hit"] for r in rows), "any_hit": sum(r["any_hit"] for r in rows)}
            lines += [f"已确认的检出用例 {len(rows)} 个；有候选 {res['samples'][g]['with_candidate']} 个；"
                      f"第一候选命中修复位置 {res['samples'][g]['top_hit']} 个；任一候选命中 {res['samples'][g]['any_hit']} 个。", ""]
            for r in rows[:6]:
                v = cmp_["values"].get(r["id"], {})
                lines += [f"## 用例 {r['id']}：`{r['sc']}` {' '.join(cases[r['id']]['args'])}", "",
                          "现象：" + "；".join(f"{k} 返回 {json.loads(x)[0]}" for k, x in v.items()), "",
                          f"候选（第一候选{'命中' if r['top_hit'] else '未命中'}，任一候选{'命中' if r['any_hit'] else '未命中'}）："]
                lines += [text(c) for c in r["candidates"][:4]] or ["- 没有静态来源"]
                lines.append("")
        else:
            s = cmp_["checked"]["cur_riscv"]
            out = {}
            for a, cl in s["clusters"].items():
                n = sum(1 for m in cl.values() if candidates(cases[m[0]], idx, probes, kernels))
                out[a] = {"clusters": len(cl), "with_candidate": n}
            res["current"] = out
            lines += ["当前版本（没有已知缺陷）上与众不同的簇：" + "；".join(
                f"{a} 方向 {v['clusters']} 簇，其中 {v['with_candidate']} 簇有候选" for a, v in out.items()), ""]
            for k, m in list(s["clusters"].get("riscv", {}).items())[:6]:
                cs = candidates(cases[m[0]], idx, probes, kernels)
                lines += [f"## riscv 与众不同：{k}（{len(m)} 个用例，例 {m[0]}：{' '.join(cases[m[0]]['args'])}）", ""]
                lines += [text(c) for c in cs[:3]] or ["- 没有静态来源"]
                lines.append("")
        (HERE / "report" / f"{g}.md").write_text("\n".join(lines) + "\n", encoding="utf8")
    (HERE / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf8")
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
