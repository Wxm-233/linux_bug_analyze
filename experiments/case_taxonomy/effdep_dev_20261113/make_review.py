"""Write out/review_CUR_riscv.md from the 40-item review sample and Claude's manual judgements (criteria 八.3)."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
d = json.load(open(HERE / "out/CUR_riscv.json", encoding="utf-8"))
NOT, SUS, UNK = "不是", "疑似真问题", "判断不了"
R = {
 "flush_dcache": (NOT, "x86 的数据缓存与指令/DMA 一致，不需要刷数据缓存，空实现是设计如此"),
 "arch_clear_hugetlb_flags": (NOT, "只有带架构私有页标志的架构需要清；x86 没有这类标志"),
 "pte_batch_hint": (NOT, "只有 arm64 有连续页表项（contpte）提示；通用实现返回 1 是正确的保守值"),
 "syscall_get_arch": (SUS, "riscv64 默认开 COMPAT（32 位用户态），但 syscall_get_arch 对 32 位任务也返回 AUDIT_ARCH_RISCV64，seccomp.h 也没有定义 SECCOMP_ARCH_COMPAT；arm64 会区分 compat 任务。审计记录和 seccomp 过滤器可能把 32 位任务当成 64 位。工具把 arm64 判成“无效果”是摘要误判（它依赖任务），但指向的差异是真的"),
 "user_disable_single_step": (NOT, "riscv 没有用户态硬件单步，通用空实现是设计如此"),
 "ptrace_disable": (NOT, "arm64、x86 在这里关硬件单步；riscv 没有硬件单步，空实现是设计如此"),
 "arch_swap_restore": (NOT, "只用于 arm64 MTE 标签恢复，其他架构没有标签"),
 "arch_dup_mmap": (NOT, "x86 复制 LDT/pkey，arm64 复制 MTE/GCS 状态；riscv 没有这些状态"),
 "in_gate_area_no_mm": (NOT, "只有 x86 有 vsyscall 页"),
 "perf_arch_guest_misc_flags": (NOT, "只有 x86 提供客户机 perf 标志"),
 "kprobe_fault_handler": (NOT, "通用实现是 kprobes 未用时的返回 0；riscv 实现在 arch/riscv/kernel/probes 中，默认配置的范围内未看到，属抽取范围问题，不是缺陷"),
 "jailhouse_paravirt": (NOT, "Jailhouse 只支持 x86，x86 侧返回 false 是对的"),
 "resilient_virt_spin_lock": (NOT, "只有 x86 有虚拟化下的自旋锁回退"),
 "destroy_context": (NOT, "x86 要释放 LDT；riscv 的 init_new_context 不分配资源，无需释放"),
 "cpc_write_ffh": (NOT, "FFH 寄存器写各架构按需实现，arm64 不支持返回 -EOPNOTSUPP 是设计如此"),
 "ptep_set_access_flags": (NOT, "资源是按值传入的 entry，“产生效果”对按值参数没有意义；riscv 实际写了 ptep。工具误判"),
 "perf_reg_validate": (NOT, "riscv 按掩码返回 -EINVAL 或 0，依赖输入；摘要把“只返回常量”误当成无效果"),
 "execute_only_pkey": (NOT, "只有支持保护键的架构有效果"),
 "__arch_update_vdso_clock": (NOT, "只有 arm64 需要在 vDSO 数据里补架构字段"),
 "clocksource_arch_init": (NOT, "x86 在这里校验 vDSO 时钟模式，其他架构用通用空实现，设计如此"),
 "arch_hugetlb_migration_supported": (NOT, "x86 用通用默认，按页大小判断可迁移性，设计如此"),
 "arch_tlbbatch_should_defer": (NOT, "批量刷 TLB 的延迟优化只有 x86 实现；riscv 返回 false 只是不启用优化"),
}
rows, cnt = [], {}
for i, c in enumerate(d["review_sample"], 1):
    k = next(k for k in R if c["interface"].startswith(k))
    v, why = R[k]
    cnt[v] = cnt.get(v, 0) + 1
    h = "；".join(f"{a} {e['effect']}" for a, e in c["horizontal"].items())
    rows.append(f"| {i} | `{c['fn']}` {c['file']}:{c['line']} | `{c['interface']}` | {'/'.join(c['forms'])} | {h} | {v} | {why} |")
out = ["# 当前版本 riscv：40 条定性成立候选的人工核对", "",
       f"抽样：定性成立 {d['qualified']} 条中按 Random(20261113) 抽 40 条（判据第八节第 3 条）。核对人：Claude，读的是 `/root/repos/linux`（7.3-rc2）源码。", "",
       "结果：" + "，".join(f"{k} {v} 条" for k, v in sorted(cnt.items())) + "。疑似真问题的 2 条是同一个根因（`syscall_get_arch`），按根因算 1 个。按规则不对外报告。", "",
       "| # | 位置 | 接口 | 形态 | 横向比对 | 判断 | 理由 |", "|---|---|---|---|---|---|---|"] + rows
(HERE / "out/review_CUR_riscv.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print(cnt)
