"""xvlift criteria 三.4: lifted candidates -> review.txt, review.json. WSL."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "p1check_20261115"))
import p1check as C  # noqa: E402

tab = json.loads((CT / "xvdom_20261116/table2.json").read_text())["table"]
h = json.loads((HERE / "head.json").read_text())
lifted = h["lifted_list"]
ranked = h["ranked"][:30]
GW = {"R": "只对 present 项有定义的读接口", "MG": "只对 present 项有定义的修改接口", "S": "只对交换格式项有定义的读接口",
      "MS": "只对交换格式项有定义的修改接口"}


def chain(name, depth=0):
    e = lifted.get(name)
    if not e or depth > 5:
        return []
    out = [f"{name}（{e['file']}，L{e['level']}）← " + "；".join(e["from"])]
    for fr in e["from"]:
        callee = fr.split("@")[0]
        for k in lifted:
            if k.split("@")[0] == callee:
                out += chain(k, depth + 1)
    return out


items = []
for i, r in enumerate(ranked, 1):
    items.append({"k": i, "file": r["file"], "line": r["line"], "func": r["func"], "H": f"{r['H']}@{r['arg']}", "A": r["A"],
                  "via": r["via"], "group": r["group"], "level": r["level"], "obj": r["obj"], "M": tab[r["A"]]["M"],
                  "not_blind_for_claude": (r["file"], r["func"]) in {("mm/rmap.c", "folio_referenced_one"), ("mm/memory.c", "insert_page_into_pte_locked")}})
blobs = C.cat_files("df2908090cda", sorted({d["file"] for d in items}))
out = []
for d in items:
    src = blobs[d["file"]].split("\n")
    a, b = max(1, d["line"] - 30), min(len(src), d["line"] + 8)
    out += ["=" * 90,
            f"[{d['k']}] {d['file']}:{d['line']}  函数 {d['func']}  调用辅助接口 {d['H']}（第 {d['H'].split('@')[1]} 个参数，对象 {d['obj']}）",
            f"    辅助接口内部没守卫地用了 {', '.join(d['via'])}（{GW[d['group']]}）；编码表：{d['A']} 在 {', '.join(d['M'])} 上对定义域外的项出错",
            "    提升链：" + " | ".join(chain(d["H"]))]
    out += [f"{'>>' if i == d['line'] else '  '}{i:5d} {src[i - 1]}" for i in range(a, b + 1)]
(HERE / "review.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
(HERE / "review.json").write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
print("items", len(items))
