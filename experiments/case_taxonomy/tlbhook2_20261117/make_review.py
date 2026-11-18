"""tlbhook2 criteria 三.4: candidates not reviewed in v1 -> review.txt, review.json (WSL, read-only)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "p1check_20261115"))
import p1check as C  # noqa: E402

REV = "df2908090cda"
new = json.loads((HERE / "new_vs_v1.json").read_text())["new"]
RULE = {"R1": "公共侧：调用了 flush_cache_vmap(start, end)，但某个架构的 flush_cache_vmap 只对部分地址区域生效，这次映射的区域不在其中",
        "T3": "公共侧：flush_cache_page 所在的同一分支（最内层花括号块及其条件头）里出现 PMD 大页写法，可能在大页上用了按页刷"}
out, items = [], []
for k, x in enumerate(new, 1):
    it = {"k": k, "rule": x["rule"], "file": x["file"], "func": x["func"], "line": x["line"], "what": x.get("what"),
          "arch": x.get("arch"), "region": x.get("region"), "covered": x.get("covered")}
    items.append(it)
    out += ["=" * 100, f"[{k}] {RULE[x['rule']]}", f"    {x['file']}:{x['line']}  函数 {x['func']}  写法 {x.get('what')}"]
    if x["rule"] == "R1":
        out.append(f"    架构 {x['arch']}：flush_cache_vmap 只对 {', '.join(x['covered'])} 区域生效；这次映射判断为 {x['region']} 区域")
        g = C.git("show", f"{REV}:arch/{x['arch']}/include/asm/cacheflush.h").split("\n")
        i = next(n for n, l in enumerate(g) if "void flush_cache_vmap(" in l)
        out += [f"    | {l}" for l in g[max(0, i - 14):i + 8]]
    src = C.git("show", f"{REV}:{x['file']}").split("\n")
    a, b = max(1, x["line"] - 50), min(len(src), x["line"] + 12)
    out += [f"{'>>' if i == x['line'] else '  '}{i:5d} {src[i - 1]}" for i in range(a, b + 1)]
(HERE / "review.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
(HERE / "review.json").write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
print("items", len(items))
