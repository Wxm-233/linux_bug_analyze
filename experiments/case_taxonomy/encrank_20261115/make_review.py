"""Code context for the not-yet-reviewed entries of the new top 30 (criteria 四.3) -> review_new.txt. WSL."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "p1check_20261115"))
import p1check as C  # noqa: E402

new = json.loads((HERE / "new_review.json").read_text(encoding="utf-8"))
blobs = C.cat_files("df2908090cda", sorted({d["file"] for d in new}))
L = []
for k, d in enumerate(new, 1):
    src = blobs[d["file"]].split("\n")
    a, b = max(1, d["line"] - 30), min(len(src), d["line"] + 8)
    L += ["=" * 90, f"[{k}] {d['file']}:{d['line']}  函数 {d['func']}  接口 {d['A']}  编码表：在 {', '.join(d['M']) or '—'} 上对某些非 present 项读错/改坏"]
    L += [f"{'>>' if i == d['line'] else '  '}{i:5d} {src[i - 1]}" for i in range(a, b + 1)]
(HERE / "review_new.txt").write_text("\n".join(L) + "\n")
for k, d in enumerate(new, 1):
    print(k, d["file"], d["line"], d["func"], d["A"], d["M"])
