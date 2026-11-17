"""out/review_CUR_riscv.md: manual review of all current-version candidates left by the effect-match filter (criteria 四.4)."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
d = json.load(open(HERE / "out/CUR_riscv.json", encoding="utf-8"))
J = {
 "acpi_os_ioremap": ("不是", "unmap = true 记录映射来源，之后对称释放；被跳过的 rcu_read_unlock 是另一条分支的解锁，与 ioremap 的效果无关"),
 "pte_modify": ("真实依赖，当前满足", "跳过写时复制依赖 pte_modify 保留 _PAGE_UFFD；x86 显式、arm64 和 riscv 用掩码保留，三个支持 USERFAULTFD_RWP 的架构都满足（详见 effdep5 核对）"),
 "mask_irq": ("不是", "unmask = 1 记录“之后要恢复”，状态记录"),
 "local_set": ("不是", "read = 0 是读取偏移量；跳过的是初始化数据页的另一条分支"),
 "pte_none": ("不是", "nr_ptes = 1 是批处理步长"),
 "cpu_relax": ("不是", "ret = false 是返回值，循环里重试读 seqcount"),
 "memset": ("不是", "nr_pages = 0 是计数"),
 "verbose": ("不是", "日志打印的开关（has_use、printed、first），与 verbose 的效果无关"),
}
rows, cnt = [], {}
for i, c in enumerate(d["candidates_list"], 1):
    v, why = J[c["interface"]]
    cnt[v] = cnt.get(v, 0) + 1
    rows.append(f"| {i} | `{c['fn']}` {c['file']}:{c['call_line']} | `{c['interface']}` | `{c['flag']} = {c['const']}` | "
                f"{'、'.join(c['skipped_all'][:3])} | {'+'.join(c['effect_match'])} | {v} | {why} |")
out = ["# 当前版本 riscv：效果对上效果之后的候选人工核对", "",
       f"过滤前 {d['candidates_before_filter']} 个候选，过滤后剩 {d['candidates']} 个，全部核对。判断标准同 effdep5 修订 1 第 3 条。核对人 Claude。", "",
       "结果：" + "，".join(f"{k} {v}" for k, v in cnt.items()) + "。", "",
       "| # | 位置 | 接口 | 标志 | 被跳过的调用 | 重合类别 | 判断 | 理由 |", "|---|---|---|---|---|---|---|---|"] + rows
(HERE / "out/review_CUR_riscv.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print(cnt)
