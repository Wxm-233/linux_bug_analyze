"""tlbhook criteria 四.4: all HEAD candidates -> review.txt, review.json (WSL, read-only)."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "p1check_20261115"))
import p1check as C  # noqa: E402

REV = "df2908090cda"
h = json.loads((HERE / "head.json").read_text())
items = []
for x in h["arch_rules"]:
    items.append({"rule": x["rule"], "arch": x["arch"], "hook": x["hook"]})
for x in h["common"]:
    items.append({"rule": x["rule"], "file": x["file"], "func": x["func"], "line": x["line"], "what": x["what"], "archs": x["archs"]})
RULE = {"T1b": "架构侧：update_mmu_cache 只刷本地 TLB（其他 CPU 可能仍缓存着旧的无效项）",
        "T2": "公共侧：建立或修改内核映射后，这个函数和它的调用者里都没有找到 flush_cache_vmap / flush_tlb_kernel_range 等刷新",
        "T3": "公共侧：在 PMD 大页附近用了按页刷的 flush_cache_page（或第 3 个参数不是页框号）",
        "T4": "公共侧：内核写页内容后映射给用户，没有 flush_dcache_page"}
out = []
for k, it in enumerate(items, 1):
    it["k"] = k
    out += ["=" * 100, f"[{k}] {RULE[it['rule']]}"]
    if it["rule"] == "T1b":
        g = C.git("grep", "-n", "update_mmu_cache", REV, "--", f"arch/{it['arch']}/include/asm/", f"arch/{it['arch']}/mm/")
        out.append(f"    架构 {it['arch']}，相关定义位置：")
        out += ["    " + ln for ln in g.split("\n")[:12] if ln]
        continue
    out.append(f"    {it['file']}:{it['line']}  函数 {it['func']}  写法 {it['what']}")
    out.append(f"    相关钩子不为空的架构：{', '.join(it['archs'])}")
    src = C.git("show", f"{REV}:{it['file']}").split("\n")
    a, b = max(1, it["line"] - 25), min(len(src), it["line"] + 12)
    out += [f"{'>>' if i == it['line'] else '  '}{i:5d} {src[i - 1]}" for i in range(a, b + 1)]
(HERE / "review.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
(HERE / "review.json").write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding="utf-8")
print("items", len(items))
