"""orddom criteria 四.3: top-30 candidates -> review.txt, review.json. WSL."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "p1check_20261115"))
import p1check as C  # noqa: E402

h = json.loads((HERE / "head.json").read_text())
S = h["sets"]["S"]
items = []
for i, r in enumerate(h["ranked"][:30], 1):
    items.append({"k": i, "file": r["file"], "func": r["func"], "line": r["line"], "line1": r["line1"], "sources": r["sources"],
                  "bases": r["bases"], "M": r["M"]})
blobs = C.cat_files("df2908090cda", sorted({d["file"] for d in items}))
out = []
for d in items:
    src = blobs[d["file"]].split("\n")
    pat = re.compile(r"\b(" + "|".join(map(re.escape, d["sources"])) + r")\b")
    hit = [n for n in range(d["line"], min(d["line1"], len(src)) + 1) if pat.search(src[n - 1])]
    show = sorted({x for n in hit for x in range(max(d["line"], n - 6), min(d["line1"], n + 4) + 1)})
    out += ["=" * 90,
            f"[{d['k']}] {d['file']}:{d['line']}-{d['line1']}  函数 {d['func']}  用到的大阶数来源 {', '.join(d['sources'])}"
            f"（展开后是 {', '.join(d['bases'])}）",
            f"    常量表：在 {', '.join(d['M'])} 上，该来源大于 MAX_PAGECACHE_ORDER；函数里没有出现任何页缓存上限守卫",
            f"  {d['line']:5d} {src[d['line'] - 1]}"]
    prev = d["line"]
    for n in show:
        if n > prev + 1:
            out.append("        ...")
        out.append(f"{'>>' if n in hit else '  '}{n:5d} {src[n - 1]}")
        prev = n
(HERE / "review.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
(HERE / "review.json").write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
print("items", len(items), "lines", len(out))
