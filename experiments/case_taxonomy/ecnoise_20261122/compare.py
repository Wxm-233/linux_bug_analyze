"""ecnoise criteria 三 G1/G3/G4: where each round-2 candidate row went, and which round-3 rows are new. WSL.

    python3 compare.py   -> compare.json, compare.md
"""
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REV = "df2908090cda368b01ff43709f51890076c56157"
R2 = json.loads((HERE.parent / "ecscan_20261122" / "ec_df2908090cda.json").read_text(encoding="utf-8"))
R3 = json.loads(Path(f"/root/work/ec_cache/r3/{REV}.json").read_text(encoding="utf-8"))
D3 = Path("/root/work/ec_cache/r3/df2908090cda")
beh3 = {p.stem[4:]: json.loads(p.read_text(encoding="utf-8"))["laws"] for p in D3.glob("beh_*.json")}
devs2 = json.loads((HERE.parent / "ecscan_20261122" / "ec_deviations.json").read_text(encoding="utf-8"))
devs3 = json.loads((D3 / "deviations.json").read_text(encoding="utf-8"))
NOISE29 = {f"E{i:02d}" for i in [5, 6] + list(range(7, 16)) + list(range(17, 35))}


def rk(c):
    return (c["arch"], c["func"], c["class"])


def why_gone(c):
    p = c["example"].split("|")
    if p[0] != "PT":
        return "交换族（不应变化）"
    _, cons, prot, mod, obs = p
    b = c["example_build"]
    L = beh3.get(b, {})
    lv = obs.split("_")[0]
    if f"PT|{cons}|folded" in L:
        return "规则3：该级在该构建上是折叠层"
    if f"PT|{cons}|nohuge" in L:
        return f"规则2：该构建没有 {lv}_mkhuge"
    chain = f"{cons}>{lv}_mkhuge" if (cons in ("pfn_pmd", "pfn_pud") or obs == f"{lv}_huge") else cons
    if f"PT|{chain}|{obs}|constobs" in L or f"PT|{cons}|{obs}|constobs" in L:
        return "规则1：该构建上的观察对全符号输入是常量"
    # the deviant build still behaves the same; did the majority lose its votes?
    others = Counter()
    for bb, LL in beh3.items():
        if bb in c["builds"]:
            continue
        if f"PT|{chain}|{obs}|constobs" in LL:
            others["规则1"] += 1
        if f"PT|{cons}|folded" in LL:
            others["规则3"] += 1
        if f"PT|{cons}|nohuge" in LL:
            others["规则2"] += 1
    tag = "，".join(f"{k} {v} 个构建" for k, v in others.items())
    if chain != cons:
        return f"规则2：加 {lv}_mkhuge 后的组合" + (f"（另：多数一方 {tag} 不再投票）" if tag else "")
    return f"多数一方不再投票（{tag}）" if tag else "其他（规律不再形成）"


r3keys = {rk(c): c for c in R3["cands"]}
r2keys = {rk(c) for c in R2["cands"]}
rows = []
for i, c in enumerate(R2["cands"], 1):
    eid = f"E{i:02d}"
    k = rk(c)
    if k in r3keys:
        rows.append({"id": eid, "row": f"{c['arch']} {c['func']} {c['class']}", "fate": "仍在", "noise29": eid in NOISE29,
                     "n2": c["n"], "n3": r3keys[k]["n"], "builds3": r3keys[k]["builds"]})
    else:
        rows.append({"id": eid, "row": f"{c['arch']} {c['func']} {c['class']}", "fate": "消去", "why": why_gone(c), "noise29": eid in NOISE29})
new = [c for c in R3["cands"] if rk(c) not in r2keys]
sw2 = sorted((d["key"], d["build"]) for d in devs2 if d["key"].startswith("SW"))
sw3 = sorted((d["key"], d["build"]) for d in devs3 if d["key"].startswith("SW"))
g = {"G1_交换族偏离相同": sw2 == sw3, "交换族偏离数": [len(sw2), len(sw3)],
     "G1_交换族行": [rk(c) for c in R3["cands"] if c["family"] == "SW"],
     "G1_mips_pfn_pte截断行": any(c["func"] == "pfn_pte" and c["class"].startswith("截断") for c in R3["cands"]),
     "G3_29行中消去": sum(1 for r in rows if r["noise29"] and r["fate"] == "消去"),
     "G3_E01至E04仍在": all(r["fate"] == "仍在" for r in rows[:4]),
     "新行数": len(new), "第三轮行数": len(R3["cands"]),
     "偏离": {"第二轮": R2.get("deviations_by_family"), "第三轮": R3.get("deviations_by_family")},
     "规律": {"第二轮": R2.get("laws_by_family"), "第三轮": R3.get("laws_by_family")}}
(HERE / "compare.json").write_text(json.dumps({"gates": g, "rows": rows, "new": new}, indent=1, ensure_ascii=False), encoding="utf-8")
L = ["| 第二轮行 | 内容 | 去向 | 原因 / 第三轮组合数 |", "|---|---|---|---|"]
for r in rows:
    detail = r.get("why") or "组合 {} → {}，{}".format(r["n2"], r["n3"], ",".join(r["builds3"]))
    tag = "" if r["noise29"] else "（不在 29 行内）"
    L.append(f"| {r['id']}{tag} | {r['row']} | {r['fate']} | {detail} |")
L += ["", "新行：", "", "| 架构 | 接口 | 类别 | 组合数 | 构建 | 示例 |", "|---|---|---|---|---|---|"]
for c in new:
    L.append(f"| {c['arch']} | {c['func']} | {c['class']} | {c['n']} | {','.join(c['builds'])} | `{c['example']}` |")
(HERE / "compare.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print(json.dumps(g, ensure_ascii=False, indent=1))
print("\n".join(L))
