"""out/review_CUR_riscv.md: Claude's manual judgements on the 40-interface review sample (effdep4 criteria 二)."""
import collections
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
d = json.load(open(HERE / "out/CUR_riscv.json", encoding="utf-8"))
NOT, UNK, SUS = "不是", "判断不了", "疑似真问题"
SPUR = "特性签名是巧合（多数 64 位新架构都选的符号）"
F = lambda why: (NOT, why, "riscv 没有这项特性")
CB = (NOT, "工具误判：riscv 经回调产生效果，闭包看不到", "回调")
VAL = (NOT, "工具误判：返回新值的页表项函数", "纯值函数")
R = {
 "arch_probe_nr_irqs": F("按中断控制器探测中断数，riscv 用通用值"),
 "__cpu_die": F("riscv 用 HOTPLUG_CORE_SYNC_DEAD 的通用流程"),
 "copy_from_kernel_nofault_allowed": (UNK, "多数架构拒绝用户空间地址；riscv（和 arm64 一样）靠 SUM 位让访问出错再由异常表兜底，语义不同，需要专家判断", "判断不了"),
 "arch_mmap_check": F("arm、sparc 对 MAP_FIXED 地址的额外限制"),
 "vtime_account_hardirq": F("powerpc、s390 的原生虚拟 CPU 时间统计"),
 "vtime_account_softirq": F("powerpc、s390 的原生虚拟 CPU 时间统计"),
 "destroy_context": F("x86 释放 LDT；riscv 不分配"),
 "arch_dup_mmap": F("x86 复制 LDT/pkey、arm64 复制 MTE/GCS 状态"),
 "module_arch_cleanup": F("释放模块的架构私有展开表等"),
 "arch_exit_to_user_mode_work": F("arm64、s390 返回用户态前的私有工作"),
 "arch_release_task_struct": (NOT, "工具误判：riscv 在这里释放向量上下文", "工具"),
 "huge_pte_mkuffd": VAL, "pte_modify": VAL, "pte_mkwrite": VAL,
 "arch_irq_stat_cpu": F("x86、powerpc 在 /proc/stat 里多报的中断计数"),
 "arch_exit_mmap": F("x86 LDT/pkey、powerpc 的私有清理"),
 "ptrace_disable": F("arm64、x86 在这里关硬件单步，riscv 没有硬件单步"),
 "memory_block_size_bytes": F("x86、powerpc、s390 按固件计算内存块大小，riscv 用默认值合理"),
 "set_direct_map_invalid_noflush": CB, "set_direct_map_default_noflush": CB, "set_memory_ro": CB,
 "arch_jump_label_transform_static": F("csky、mips 的启动期跳转标签处理"),
 "user_enable_single_step": F("riscv 没有硬件单步，公共层先用 arch_has_single_step() 判断"),
 "in_gate_area": F("只有 arm、x86 有 vsyscall/向量页"),
 "Assert": (NOT, "名叫 Assert 的宏，不是架构接口", "工具"),
 "flush_icache_pages": F("riscv 在 set_pte_at 里刷指令缓存"),
 "arch_bpf_stack_walk": F("BPF 异常支持专用，riscv JIT 不支持 BPF 异常"),
 "wrprotect_ptes": (NOT, "工具误判：riscv 用通用实现逐项写保护", "工具"),
 "flush_kernel_vmap_range": F("缓存别名架构专用（签名没找到 ARCH_HAS_CPU_CACHE_ALIASING，因为 arm 等不全选）"),
 "efi_get_max_initrd_addr": F("arm、arm64 对 EFI 加载 initrd 的地址上限，riscv64 没有这个限制"),
 "syscall_get_arch": (SUS, "riscv64 默认开 COMPAT，但对 32 位任务也返回 AUDIT_ARCH_RISCV64，也没有 SECCOMP_ARCH_COMPAT；arm64 等区分 compat 任务（同第一版的疑点）。定性依据的特性签名 ARCH_SPARSEMEM_ENABLE 是巧合，排进前 50 也是碰巧", "疑似真问题"),
 "arch_vma_access_permitted": F("保护键/MTE 的访问检查"),
 "module_arch_freeing_init": F("arm、parisc、s390 的模块私有数据"),
 "arch_start_context_switch": F("x86 半虚拟化惰性模式、sparc 的私有处理"),
 "arch_prctl_spec_ctrl_set": F("推测执行缓解的 prctl，riscv 没提供这类缓解"),
 "arch_prctl_spec_ctrl_get": F("推测执行缓解的 prctl，riscv 没提供这类缓解"),
 "user_access_save": F("x86、powerpc 在插桩/报告代码前关掉用户访问；riscv 和 arm64 都自己写了空实现，硬件保护机制不同"),
 "pmdp_test_and_clear_young": (NOT, "工具误判：riscv 在透明大页配置下有自己的实现，事实里没收录", "工具"),
 "arch_free_page": F("powerpc、s390 的协作内存管理"),
 "arch_enter_from_user_mode": F("x86、s390、powerpc 的调试检查"),
}
rows, cnt, why_cnt = [], collections.Counter(), collections.Counter()
for k, n in enumerate(d["review_sample"], 1):
    v, why, cat = R[n]
    r, q, g = d["all_q"][n]
    if q == "Q-特性" and v != SUS:
        cat = SPUR
    cnt[v] += 1
    why_cnt[cat] += 1
    rows.append(f"| {k} | `{n}` | {r} | {q} | {'、'.join((g or [])[:3])} | {v} | {why} |")
prev = collections.Counter(d["prev_review"].values())
qual = sum(d["by_q"][k] for k in ("Q-特性", "Q-多数", "Q-类别"))
out = ["# 当前版本 riscv：40 个定性成立接口的人工核对（第四版）", "",
       f"定性成立 {qual} 个接口（Q-特性 {d['by_q']['Q-特性']}、Q-多数 {d['by_q']['Q-多数']}、Q-类别 {d['by_q']['Q-类别']}），按 Random(20261113) 抽 40 个。核对人 Claude。", "",
       "结果：" + "，".join(f"{k} {v}" for k, v in cnt.most_common()) + "。按原因：" + "，".join(f"{k} {v}" for k, v in why_cnt.most_common()) + "。", "",
       f"第三版核对过的 40 个接口在本轮的去向：{dict(prev)}（None 表示不在清单里）。", "",
       "| # | 接口 | 排名 | 定性 | 特性签名（前 3 个） | 判断 | 理由 |", "|---|---|---|---|---|---|---|"] + rows
(HERE / "out/review_CUR_riscv.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print(dict(cnt), dict(why_cnt), dict(prev))
