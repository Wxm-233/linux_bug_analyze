"""ecunreach G4 (rule-4 rows: the key itself on every build; rule-5 rows: before -> after as before): evidence for the rows added at df against ecsrc's 25 -- per build, behaviour before / after the modifier for each
protection constant (as ecprot_20261122/review/evidence.py), and packets.md for the blind review."""
import json
from collections import Counter
from pathlib import Path
D = Path("/root/work/ec_cache/r9/df/df2908090cda")
R = json.loads(Path("/root/work/ec_cache/r9/df/df.json").read_text())["cands"]
base = json.loads(Path("/root/work/ec_cache/r8/df/df.json").read_text())["cands"]
bk = {(c["arch"], c["func"], c["class"]) for c in base}
laws = json.loads((D / "laws.json").read_text())
beh = {f.stem[4:]: json.loads(f.read_text())["laws"] for f in D.glob("beh_*.json")}
out = []
for c in [c for c in R if (c["arch"], c["func"], c["class"]) not in bk]:
    _, cons, prot, mod, obs = c["example"].split("|")
    if "保持" not in c["class"] and "改变" not in c["class"]:      # rule 4: per-protection shape law
        law = laws.get(f"PTP|{cons}|{prot}|{mod}|{obs}")
        per = {b: {prot: (L.get(f"PT|{cons}|{prot}|{mod}|{obs}") or {}).get("beh", "（无此组合）")} for b, L in sorted(beh.items())
               if f"PT|{cons}|{prot}|{mod}|{obs}" in L}
        out.append({"row": {k: c[k] for k in ("arch", "func", "file", "line", "class", "n", "builds", "example", "locs")}, "law": law,
                    "per_build": per, "rule": 4})
        continue
    law = laws.get(f"PTM|{cons}|{mod}|{obs}")
    per = {}
    for b, L in sorted(beh.items()):
        pv = {}
        for k, v in L.items():
            q = k.split("|")
            if q[0] == "PT" and len(q) == 5 and q[1] == cons and q[4] == obs and q[3] == "-":
                after = L.get(f"PT|{cons}|{q[2]}|{mod}|{obs}")
                if after:
                    pv[q[2]] = f"{v['beh']} -> {after['beh']}"
        if pv:
            per[b] = pv
    out.append({"row": {k: c[k] for k in ("arch", "func", "file", "line", "class", "n", "builds", "example", "locs")}, "law": law,
                "per_build": per})
here = Path(__file__).resolve().parent
(here / "evidence.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

L = ["# 盲审材料：编码一致性引擎（不可达分支一轮）在 df2908090cda 上新增的 %d 行候选\n" % len(out),
     "## 这些候选怎么来的\n",
     "分析器在 21 个构建上自动组合页表接口、逐位符号求值，再跨构建多数表决。这一轮的变化是：求值走到 `__builtin_unreachable`（如 `BUG()` 之后）的运行模式不再参加合并，"
     "因此 ppc64le（radix 模式）开始参加 PUD 级表决，PUD 级可比构建由 3 个（x86_64、arm64、riscv64_thp）变为 4 个；ppc64le_hash 的 PUD 级记为不适用（hash 不支持 PUD 大页）。"
     "新增行来自两条规则：\n",
     "- **按保护值的形状规律（规则 4）**：对同一个保护常量 prot，比较各构建上 `o(m(T_mkhuge(pfn_T(pfn, prot))))` 的真假（m 可以为空，记作 `-`），"
     "≥3 个构建可比、多数超过一半就形成规律，与多数不同的构建是偏离，类别记“多数值→该构建值|o”，例如“true→false|pud_leaf”表示多数为真、该构建为假。\n",
     "- **修改保持性（规则 5）**：对每个（构造、修改 m、观察 o），在每个构建上比较 `o(x)` 与 `o(m(x))`，所有两者都能确定的保护常量上都相等记“m 保持 o”，否则记“改变”；"
     "跨构建表决，偏离记“保持→改变|o”或“改变→保持|o”。\n",
     "记号：`const:0` 假；`const:1`、`const:other` 真；`imprecise` 求值不精确（不参加）；`unsup` 不支持；`runtime-dependent` 依赖运行时判断（不参加）。"
     "分析器只看头文件（以及本轮补上的 powerpc .c 函数），**不知道这些组合在内核里会不会被这样调用**。ppc64le 有 radix 和 hash 两种运行模式，"
     "ppc64le_hash 只有 hash 模式。\n",
     "## 构建配置\n",
     "x86_64、arm64、riscv64 分别是 `/root/work/boundary_build/{x86_64,arm64,riscv}_defconfig/.config`；riscv64_thp 是 riscv64 再打开 `TRANSPARENT_HUGEPAGE`；"
     "rv32_abi 是 `/root/work/boundary_build/closure_20261108_rv32_abi/.config`；i386 是 `/root/work/wtrange/i386/.config`；其余构建是 "
     "`/root/work/swapsym/cfg_<构建名>/.config`。也可以直接看 `/root/work/ecver/df2908090cda/cfg_<构建名>/.config`（21 个都在）。"
     "内核源码：`wsl -u root -- git -C /root/repos/linux show df2908090cda:<路径>`。\n",
     "## 候选\n"]
for i, e in enumerate(out, 1):
    r = e["row"]
    _, cons, prot, mod, obs = r["example"].split("|")
    law = e["law"] or {}
    dev = set(r["builds"])
    c0, mk = cons.split(">")
    inner = f"{mk}({c0}(pfn, prot))"
    L.append(f"### R{i}　{r['arch']} `{r['func']}`　{r['class']}\n")
    L.append(f"- 涉及构建：{', '.join(r['builds'])}；组合数 {r['n']}；位置：" + "；".join(f"{b} → `{v}`" for b, v in r["locs"].items()))
    if e.get("rule") == 4:
        expr = f"{obs}({inner})" if mod == "-" else f"{obs}({mod}({inner}))"
        L.append(f"- 规则 4：保护常量 `{prot}` 下 `{expr}` 的值")
        L.append(f"- 规律：多数构建为“{law.get('majority')}”（{law.get('n_major')}/{law.get('n_comparable')} 个可比构建）")
        L.append("- 各构建在该保护常量下的值：")
        for b, pv in e["per_build"].items():
            L.append(f"  - {b}: {pv[prot]}")
    else:
        L.append(f"- 规则 5：`{obs}({mod}({inner}))` 与 `{obs}({inner})` 比较（示例保护常量 `{prot}`）")
        L.append(f"- 规律：多数构建“{law.get('majority')}”（{law.get('n_major')}/{law.get('n_comparable')} 个可比构建）")
        L.append("- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：")
        for b, pv in e["per_build"].items():
            L.append(f"  - {b}: " + (json.dumps(pv, ensure_ascii=False) if b in dev else json.dumps(dict(Counter(pv.values())), ensure_ascii=False)))
    L.append("")
(here / "packets.md").write_text("\n".join(L), encoding="utf-8")
print(len(out))
