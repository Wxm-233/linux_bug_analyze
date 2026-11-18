"""ctxeff criteria 五.3: minority candidates on HEAD -> review.txt, review.json (WSL, read-only)."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "p1check_20261115"))
import p1check as C  # noqa: E402

REV = "df2908090cda"
h = json.loads((HERE / "head.json").read_text())
items = [c for c in h["cands"] if c["minority"]][:40]
RULE = {"X1": "公共代码在原子上下文（持自旋锁、关抢占、RCU 读侧、关中断等）里调到这个钩子，而这个架构的实现会睡眠",
        "X2": "公共代码在关中断上下文里调到这个钩子，而这个架构的实现会发 IPI 并等待（smp_call_function / on_each_cpu / riscv SBI 远程刷新）"}


def def_lines(arch, name):
    g = C.git("grep", "-n", "-E", r"^[a-z].*\b%s\s*\(|define\s+%s\(" % (re.escape(name), re.escape(name)), REV, "--",
              f"arch/{arch}/include/asm/", f"arch/{arch}/mm/")
    return [ln.split(":", 1)[1] for ln in g.split("\n") if ln][:3]


def excerpt(path, line, before, after):
    src = C.git("show", f"{REV}:{path}").split("\n")
    a, b = max(1, line - before), min(len(src), line + after)
    return [f"{'>>' if i == line else '  '}{i:5d} {src[i - 1]}" for i in range(a, b + 1)]


out, rows = [], []
for k, c in enumerate(items, 1):
    rows.append(dict(c, k=k))
    out += ["=" * 100, f"[{k}] {c['rule']}：{RULE[c['rule']]}",
            f"    钩子 {c['hook']}；架构 {c['arch']}；效果 {c['effect']}（实现该钩子的 {c['n_impl']} 个架构里有 {c['n_effect']} 个有此效果）",
            f"    架构实现的效果路径：{' -> '.join(c['witness'])}",
            f"    调用上下文示例链（从上下文来源到钩子调用点，共 {c['n_sites']} 个这样的调用点）："]
    out += ["      " + s for s in c["chain"]]
    out.append("    架构实现的定义位置：")
    for d in def_lines(c["arch"], c["hook"]):
        out.append("      " + d)
        try:
            path, ln = d.split(":")[0], int(d.split(":")[1])
            out += ["      " + x for x in excerpt(path, ln, 0, 22)]
        except (ValueError, IndexError):
            pass
        break
    m = re.match(r"(\S+):(\d+) ", c["site"])
    if m:
        out.append(f"    公共代码调用点 {c['site']}：")
        out += ["      " + x for x in excerpt(m.group(1), int(m.group(2)), 12, 6)]
(HERE / "review.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
(HERE / "review.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
print("items", len(rows))
