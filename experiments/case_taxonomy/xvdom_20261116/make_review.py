"""xvdom criteria 四.4: top-30 candidates -> review.txt, review.json. WSL."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CT = HERE.parent
sys.path.insert(0, str(CT / "p1check_20261115"))
import p1check as C  # noqa: E402

tab = json.loads((HERE / "table2.json").read_text())["table"]
ranked = json.loads((HERE / "head.json").read_text())["ranked"][:30]
WHAT = {"S": "只对交换格式项有定义的读接口；编码表：在 {M} 上对某些 present 项或空项读出 1",
        "MS": "只对交换格式项有定义的修改接口；编码表：在 {M} 上会改变 present 项或空项的值",
        "MG": "只对 present 项有定义的修改接口；编码表：在 {M} 上会改变某些非 present 项或空项的值"}
items = []
for i, r in enumerate(ranked, 1):
    t = tab[r["A"]]
    items.append({"k": i, "file": r["file"], "line": r["line"], "func": r["func"], "A": r["A"], "group": r["group"],
                  "origin": r["origin"], "M": t["M"], "detail": t["detail"],
                  "not_blind_for_claude": (r["file"], r["line"]) == ("include/linux/pgtable.h", 537)})
blobs = C.cat_files("df2908090cda", sorted({d["file"] for d in items}))
out = []
for d in items:
    src = blobs[d["file"]].split("\n")
    a, b = max(1, d["line"] - 30), min(len(src), d["line"] + 8)
    ex = "; ".join(f"{a}: {', '.join(v[:6])}{' …' if len(v) > 6 else ''}" for a, v in d["detail"].items())
    out += ["=" * 90, f"[{d['k']}] {d['file']}:{d['line']}  函数 {d['func']}  接口 {d['A']}（{d['group']} 组）  来源 {d['origin']}",
            "    " + WHAT[d["group"]].format(M=", ".join(d["M"])), f"    出错的输入类：{ex}"]
    out += [f"{'>>' if i == d['line'] else '  '}{i:5d} {src[i - 1]}" for i in range(a, b + 1)]
(HERE / "review.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
(HERE / "review.json").write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
print("items", len(items))
