"""outfmt criteria 二: annotate(row) -> (关键资源, 要观察的性质, 不算失配的条件), mechanically from engine + 特征 (sig).
row: dict with keys engine, sig, func (as in the scan tables). No engine is re-run; nothing here changes a candidate.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
XV_GROUP = {n: t["group"] for n, t in
            json.loads((HERE.parent / "xvdom_20261116" / "table2.json").read_text(encoding="utf-8"))["table"].items()}
XV_OLD = {"pte_mkuffd_wp": "pte_mkuffd", "pte_clear_uffd_wp": "pte_clear_uffd", "pmd_mkuffd_wp": "pmd_mkuffd",
          "pmd_clear_uffd_wp": "pmd_clear_uffd"}          # renamed interfaces, as xvdom.OLD / engines.eng_XV
UNDEF = "未定义形态"


def _undef(sig):
    s = f"{UNDEF}：{sig.split('|')[0]}"
    return s, s, s


def _wt(p):
    form, where, expr = p[0], p[1], "|".join(p[2:])
    if where.startswith("arg:"):
        fn, _, i = where[4:].partition("#")
        res = f"传给 {fn}() 第 {int(i) + 1} 个参数的值 `{expr}`"
    elif where.startswith("assign:"):
        res = f"赋给 `{where[7:]}` 的值 `{expr}`"
    elif where.startswith("return:"):
        res = f"返回值 `{expr}`"
    elif where == "mask":
        res = f"掩码运算 `{expr}`"
    else:
        return None
    if form == "A":
        return (res, "在 32 位架构上，这个值放得下目标类型，高位不被截掉",
                "在所有架构上它的取值都不超过目标类型的范围")
    if form == "B":
        return (res, "移位在 32 位宽度里计算时不溢出（先算移位、后扩成 64 位会丢掉高位）",
                "移位前已扩到 64 位，或移位结果在 32 位内放得下")
    if form == "C":
        return (res, "掩码与被掩的值同宽，不丢高位",
                "掩码已按被掩值的类型扩宽，或被掩值的高位本来为 0")
    return None


def _xv_need(a):
    g = XV_GROUP.get(a) or XV_GROUP.get(XV_OLD.get(a, ""))
    if g in ("R", "MG"):
        extra = "（修改接口，用在非 present 项上会把项改坏）" if g == "MG" else "（只读 present 项的接口）"
        return f"调用 {a}() 时该项是 present 项{extra}", "调用前已确认是 present 项"
    if g in ("S", "MS"):
        return (f"调用 {a}() 时该项是非 present 且非空的交换格式项（{a} 只对交换格式项有定义）",
                "调用前已确认是交换格式项（不是 present 项、不是空项）")
    return None


def annotate(row):
    e, sig = row["engine"], row["sig"]
    p = sig.split("|")
    out = None
    if e == "WT":
        out = _wt(p)
    elif e == "ORD":
        out = (f"由页大小派生的阶数/大小 {'、'.join(p)}",
               "在每种“架构 × 页大小”下都不超过页缓存上限 MAX_PAGECACHE_ORDER",
               "所有组合下都不超过上限，或使用前已和上限比较")
    elif e == "P1" and len(p) == 2:
        out = (f"页表项 `{p[1]}`（交给 {p[0]}()）", f"调用 {p[0]}() 时该项是 present 项（{p[0]} 只对 present 项有定义）",
               "调用前已确认 present，或这条路径上不可能出现非 present 项")
    elif e == "XV" and p[0] in ("dom", "lift"):
        a, obj = (p[1], p[2]) if p[0] == "dom" else (p[2], p[3])
        need = _xv_need(a)
        if need:
            if p[0] == "dom":
                res = f"页表项 `{obj}`（交给 {a}()）"
            else:
                h, _, k = p[1].partition("@")
                res = f"页表项 `{obj}`（经辅助函数 {h}() 第 {int(k) + 1} 个参数传入，{h} 内部对它调用 {a}()）"
            out = (res, need[0], need[1])
    elif e == "TLB":
        if p[0] == "T2":
            out = (f"内核页表的改动：{p[1]}（建立、改动或释放内核映射）",           # amendment 1
                   "改动后本函数或调用链（向上至多 8 层）调用了 TLB/缓存刷新钩子，使改动在需要刷新的架构上生效",
                   "调用链上有刷新，或这项改动在被使用前已由其他机制保证生效（例如延迟统一刷新）")
        elif p[0] == "T3":
            out = (f"按页刷新的缓存范围：{p[1]}", "flush_cache_page 的第 3 个参数是页框号，大页按整块刷新",
                   "参数确为页框号且范围覆盖整个映射")
        elif p[0] in ("T1a", "T1b", "R1") and len(p) >= 2:
            what = f"：{p[-1]}" if p[0] == "R1" else ""
            out = (f"{p[1]} 的缓存/TLB 刷新钩子{what}", "钩子对这段映射真正生效，与同一架构其他钩子的语义一致",
                   "该架构确实不需要这项维护，或钩子已覆盖这段地址")
    elif e == "WK" and len(p) >= 6 and p[0] == "WK":
        f, arch, eff, kind, cond = p[1], p[2], p[3], p[4], "|".join(p[5:])
        how = {"conditional-effect": f"它只在 `{cond}` 成立时才做", "early-return": f"它在 `{cond}` 时提前返回、跳过"}.get(kind)
        if how:
            out = (f"弱定义 {f}() 默认实现的效果：调用 {eff}()",
                   f"{arch} 的覆盖实现在所有路径上都完成这项效果（{how}）",
                   "条件不满足的情形在该架构上本就不需要这项效果")
    elif e == "XA" and len(p) >= 4 and p[0] == "XA":
        if p[1] == "B":
            out = (f"{p[2]}() 收到的页表项（{p[3]} 实现）",
                   "架构实现对非 present 项的假设（VM_BUG_ON(!p?d_present)）与公共调用方实际传入的项一致",
                   "所有公共调用方都只传 present 项")
        elif p[1] == "A":
            out = (f"{p[2]}() 对页表项的读-清操作（{p[3]} 实现）", "读和清是原子的",
                   "调用方持锁，或该架构上不会并发修改这一项")
    elif e == "CTX" and len(p) >= 4 and p[2] in ("sleep", "ipi"):
        hook, arch, kind = p[0], p[1], p[2]
        res = f"架构钩子 {hook}() 的 {arch} 实现（{p[3]}）"
        if kind == "sleep":
            out = (res, "在调用点的上下文（原子/持锁）里调用它不会睡眠",
                   "调用点实际不在原子上下文，或这种调用走不到睡眠路径")
        else:
            out = (res, "在调用点的上下文（关中断）里调用它不会发 IPI 并等待",
                   "调用点实际没有关中断，或这种调用走不到发 IPI 的路径")
    elif e == "EC" and len(p) >= 5 and p[0] == "EC":
        fam, m, law = p[1], p[2], p[3]
        builds = next((x[3:] for x in p if x.startswith("构建 ")), "")
        if law.startswith("截断:"):
            fld = law[3:]
            out = (f"{m}() 编码的 {fld} 字段（构建 {builds}）", "合法范围内的值编码后再解码能原样读回，不被截断",
                   "该架构的合法取值本来就在编码宽度内")
        elif "→" in law and len(p) >= 6:
            a, b = law.split("→")
            obs = p[4]
            if {a, b} <= {"true", "false"}:
                out = (f"经 {m}() 处理后的页表项（构建 {builds}）",
                       f"观察 {obs}() 的结果与多数架构一致（多数为 {a}，本构建为 {b}）",
                       "差异属于架构允许的实现差异，公共代码不依赖这个值")
            elif {a, b} <= {"改变", "保持"}:
                out = (f"调用 {m}() 前后的页表项（构建 {builds}）",
                       f"{m}() 对 {obs}() 的影响与多数架构一致（多数：{a}，本构建：{b}）",
                       "差异属于架构允许的实现差异，公共代码不依赖这个值")
    return out if out else _undef(sig)
