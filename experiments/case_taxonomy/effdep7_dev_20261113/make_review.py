"""out/review_CUR_riscv.md: manual review of all current-version candidates left by the same-resource condition (criteria 三.3)."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
d = json.load(open(HERE / "out/CUR_riscv.json", encoding="utf-8"))
J = {
 "mask_irq": "共享的 desc 是中断描述符这个上下文对象；unmask = 1 记录“之后要恢复”，不是相信 mask_irq 替它做了 unmask_irq 的事",
 "local_set": "共享的 dpage 是数据页；read = 0 是读取偏移量，被跳过的初始化在另一条分支，与 local_set 无关",
 "pte_none": "共享的 new_ptep；nr_ptes = 1 是批处理步长，pte_none 只是判断，没有效果",
 "verbose": "共享的 env 是验证器的上下文对象，几乎每个调用都传它；标志是日志打印开关",
}
rows = []
for i, c in enumerate(d["candidates_list"], 1):
    rows.append(f"| {i} | `{c['fn']}` {c['file']}:{c['call_line']} | `{c['interface']}` | `{c['flag']} = {c['const']}` | "
                f"{'、'.join(c['same_res_calls'])} | {'、'.join(c['shared_resources'])} | 不是 | {J[c['interface']]} |")
out = ["# 当前版本 riscv：加“同一资源”条件后的候选人工核对", "",
       f"effdep6 过滤后 {d['candidates_effdep6']} 个，本轮剩 {d['candidates']} 个，全部核对：不是 {len(rows)}。判断标准同 effdep5 修订 1 第 3 条。核对人 Claude。", "",
       "effdep5、effdep6 找到的那条真实依赖（`do_swap_page`、`pte_modify`）按事先预期被去掉：`pte_modify(pte, ...)` 和 `do_wp_page(vmf)` 不共享实参基变量。", "",
       "| # | 位置 | 接口 | 标志 | 共享资源的被跳过调用 | 共享资源 | 判断 | 理由 |", "|---|---|---|---|---|---|---|---|"] + rows
(HERE / "out/review_CUR_riscv.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print(len(rows))
