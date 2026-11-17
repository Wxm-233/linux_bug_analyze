"""widthtrunc2 criteria 二.4: new top-30 not reviewed in v1 -> review.txt, review.json. WSL."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "p1check_20261115"))
import p1check as C  # noqa: E402

h = json.loads((HERE / "head.json").read_text())
FORM = {"A": "A 窄化：恒 64 位的值交给在 32 位架构上只有 32 位的类型", "B": "B 移位溢出：32/64 位可变的值先左移，再当 64 位用",
        "C": "C 掩码截断：64 位的值 & ~(32/64 位可变的值 …)，32 位架构上会清掉高 32 位"}
new = [r for r in h["ranked"] if not (r.get("v1_rank") and r["v1_rank"] <= 30)][:30]
items = [{"k": i, "file": r["file"], "func": r["func"], "line": r["line"], "form": r["form"], "where": r["where"], "v1_rank": r.get("v1_rank")}
         for i, r in enumerate(new, 1)]
blobs = C.cat_files("df2908090cda", sorted({d["file"] for d in items}))
out = []
for d in items:
    src = blobs[d["file"]].split("\n")
    a, b = max(1, d["line"] - 25), min(len(src), d["line"] + 6)
    out += ["=" * 90, f"[{d['k']}] {d['file']}:{d['line']}  函数 {d['func']}  形态 {FORM[d['form']]}  位置 {d['where']}",
            "    32 位组合：" + ", ".join(["arm32", "i386", "riscv32", "mips32"])]
    out += [f"{'>>' if i == d['line'] else '  '}{i:5d} {src[i - 1]}" for i in range(a, b + 1)]
(HERE / "review.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
(HERE / "review.json").write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
print("items", len(items))
