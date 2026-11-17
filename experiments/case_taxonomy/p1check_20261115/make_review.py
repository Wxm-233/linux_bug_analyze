"""Dump code context for the 30 O1 findings at HEAD (criteria 四.4) -> review_o1.txt. WSL."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p1check as C  # noqa: E402

HERE = Path(__file__).resolve().parent
h = json.loads((HERE / "head.json").read_text())
files = sorted({x["file"] for x in h["o1_top30"]})
blobs = C.cat_files("df2908090cda", files)
L = []
for k, x in enumerate(h["o1_top30"], 1):
    src = blobs[x["file"]].split("\n")
    _, _, _, spans = C.analyze_source(blobs[x["file"]], x["file"])
    fs = [s for s in spans if s[0] == x["func"] and s[1] <= x["line"] <= s[2]]
    a, b = (fs[0][1], fs[0][2]) if fs else (x["line"] - 20, x["line"] + 5)
    a = max(a, x["line"] - 45)
    b = min(b, x["line"] + 8)
    L += ["=" * 90, f"[{k}] {x['file']}:{x['line']}  函数 {x['func']}  接口 {x['accessor']}({x['arg']})  来源 {x['source']}"]
    L += [f"{'>>' if i == x['line'] else '  '}{i:5d} {src[i - 1]}" for i in range(a, b + 1)]
(HERE / "review_o1.txt").write_text("\n".join(L) + "\n")
print(len(h["o1_top30"]))
