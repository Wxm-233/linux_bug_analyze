"""ecsrc G4: evidence for the rows added at df against ecpud's 22 -- per build, behaviour before / after the modifier for each
protection constant (as ecprot_20261122/review/evidence.py), and packets.md for the blind review."""
import json
from collections import Counter
from pathlib import Path
D = Path("/root/work/ec_cache/r8/df/df2908090cda")
R = json.loads(Path("/root/work/ec_cache/r8/df/df.json").read_text())["cands"]
base = json.loads(Path("/root/work/ec_cache/r7/df/df.json").read_text())["cands"]
bk = {(c["arch"], c["func"], c["class"]) for c in base}
laws = json.loads((D / "laws.json").read_text())
beh = {f.stem[4:]: json.loads(f.read_text())["laws"] for f in D.glob("beh_*.json")}
out = []
for c in [c for c in R if (c["arch"], c["func"], c["class"]) not in bk]:
    _, cons, prot, mod, obs = c["example"].split("|")
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

L = ["# 盲审材料：编码一致性引擎（.c 定义补全一轮）在 df2908090cda 上新增的 %d 行候选\n" % len(out),
     "## 这些候选怎么来的\n",
     "分析器在 21 个构建上自动组合页表接口、逐位符号求值，再跨构建多数表决。这一轮的变化是：powerpc book3s64（ppc64le、ppc64le_hash 两个构建）"
     "原来缺函数体的 `pfn_pmd`、`pfn_pud` 等从 `arch/powerpc/mm/book3s64/pgtable.c` 补上，两个构建开始参加 PMD 级的表决；其他构建的行为没有变。"
     "下面的行都来自**修改保持性**规则：对每个（构造、修改 m、观察 o），在每个构建上比较 `o(x)` 与 `o(m(x))`，x = `pmd_mkhuge(pfn_pmd(pfn, prot))`，"
     "prot 取该构建的各个保护常量；所有两者都能确定的保护常量上都相等记为“m 保持 o”，否则记“m 改变 o”。至少 3 个构建可比、多数超过一半就形成规律，"
     "与多数不同的构建是偏离，类别记“保持→改变|o”或“改变→保持|o”。\n",
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
    L.append(f"### M{i}　{r['arch']} `{r['func']}`　{r['class']}\n")
    L.append(f"- 涉及构建：{', '.join(r['builds'])}；组合数 {r['n']}；位置：" + "；".join(f"{b} → `{v}`" for b, v in r["locs"].items()))
    c2 = cons.replace(">", "(") 
    L.append(f"- 组合：`{obs}({mod}({cons.split('>')[1]}({cons.split('>')[0]}(pfn, prot))))` 与 `{obs}({cons.split('>')[1]}({cons.split('>')[0]}(pfn, prot)))` 比较（示例保护常量 `{prot}`）")
    L.append(f"- 规律：多数构建“{law.get('majority')}”（{law.get('n_major')}/{law.get('n_comparable')} 个可比构建）")
    L.append("- 各构建（偏离构建逐个保护常量列出，其余构建给计数）：")
    for b, pv in e["per_build"].items():
        L.append(f"  - {b}: " + (json.dumps(pv, ensure_ascii=False) if b in dev else json.dumps(dict(Counter(pv.values())), ensure_ascii=False)))
    L.append("")
(here / "packets.md").write_text("\n".join(L), encoding="utf-8")
print(len(out))
