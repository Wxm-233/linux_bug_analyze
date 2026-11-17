"""Code context for the top 30 deviations at HEAD (criteria 三.3) -> review_top30.txt. WSL."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import contract as K  # noqa: E402

h = json.loads((HERE / "head.json").read_text())
top = h["deviations"][:30]
blobs = K.C.cat_files("df2908090cda", sorted({d["file"] for d in top}))
L = []
for k, d in enumerate(top, 1):
    src = blobs[d["file"]].split("\n")
    a, b = max(1, d["line"] - 30), min(len(src), d["line"] + 6)
    items = "；".join(f"{i['kind']} 缺 {i['missing']}（契约比例 {i['ratio']}，{i['n']} 个调用点）" for i in d["items"])
    L += ["=" * 90, f"[{k}] {d['file']}:{d['line']}  函数 {d['func']}  接口 {d['A']}  {items}"]
    L += [f"{'>>' if i == d['line'] else '  '}{i:5d} {src[i - 1]}" for i in range(a, b + 1)]
(HERE / "review_top30.txt").write_text("\n".join(L) + "\n")
(HERE / "top30.json").write_text(json.dumps(top, indent=1, ensure_ascii=False))
print(len(top))
for k, d in enumerate(top, 1):
    print(k, d["file"], d["line"], d["func"], d["A"], [(i["kind"], i["missing"], i["ratio"], i["n"]) for i in d["items"]])
