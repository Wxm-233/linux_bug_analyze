"""out/review_CUR_riscv.md: Claude's manual judgements on the 40-interface review sample (effdep2 criteria 三.3)."""
import collections
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
d = json.load(open(HERE / "out/CUR_riscv.json", encoding="utf-8"))
NOT, SUS, UNK = "不是", "疑似真问题", "判断不了"
VIVT = (NOT, "只有虚拟索引缓存（VIVT）或有缓存别名的架构需要；riscv 的缓存是物理索引，设计如此")
COCO = (NOT, "内存加密（机密计算）专用，riscv 主线没有这项特性")
CB = (NOT, "工具误判：riscv 的 set_memory/set_direct_map 通过页表遍历的回调改页表，闭包按函数名展开看不到")
VAL = (NOT, "工具误判：这是返回新值的纯函数，arm64 的 set_pte_bit/clear_pte_bit 被类别正则误认成写页表")
R = {
 "kvm_arch_para_features": (NOT, "KVM 客户机半虚拟化特性，riscv 客户机走 SBI，不用这套接口"),
 "__cpu_die": (NOT, "riscv 用 HOTPLUG_CORE_SYNC_DEAD 的通用流程，不需要 __cpu_die"),
 "flush_cache_dup_mm": VIVT, "flush_cache_mm": VIVT, "flush_cache_vunmap": VIVT, "flush_kernel_vmap_range": VIVT,
 "flush_anon_page": VIVT, "flush_dcache_mmap_unlock": VIVT,
 "force_dma_unencrypted": COCO, "set_memory_encrypted": COCO, "set_memory_decrypted": COCO,
 "arch_dup_mmap": (NOT, "x86 复制 LDT/pkey、arm64 复制 MTE/GCS 状态，riscv 没有这些状态"),
 "module_arch_freeing_init": (NOT, "arm/parisc/s390 释放模块时的架构私有数据，riscv 没有"),
 "arch_prctl_spec_ctrl_get": (NOT, "推测执行缓解的 prctl 接口，riscv 没有提供这类缓解，返回默认值是设计如此"),
 "Assert": (NOT, "工具误判：名字叫 Assert 的宏，不是架构接口"),
 "arch_vma_name": (NOT, "给架构特殊映射命名，riscv 用 vm_special_mapping 自带名字"),
 "arch_override_mprotect_pkey": (NOT, "保护键专用，riscv 没有"),
 "arch_vma_access_permitted": (NOT, "保护键/MTE 的访问检查，riscv 没有"),
 "flush_tlb_page": (NOT, "工具判 riscv 缺屏障；riscv 的 sfence.vma 本身对页表访问排序，arm64 才需要 dsb，架构语义不同"),
 "arch_tlbbatch_flush": (NOT, "同上，riscv 当前实现经 IPI/SBI 远程刷新，不需要单独的屏障（A043 当年的缺陷在这里，但当前版本已修）"),
 "set_memory_ro": CB, "set_direct_map_default_noflush": CB,
 "user_enable_single_step": (NOT, "riscv 没有硬件单步，公共层先用 arch_has_single_step() 判断，不会调到通用桩"),
 "ptrace_disable": (NOT, "arm64、x86 在这里关硬件单步；riscv 没有硬件单步"),
 "pte_mkold": VAL, "pte_modify": VAL, "pte_mkclean": VAL, "pte_swp_clear_exclusive": VAL, "pte_mkwrite": VAL,
 "huge_pte_mkuffd": VAL,
 "enter_lazy_tlb": (NOT, "x86、arm64 记录惰性 TLB 状态用于优化，riscv 不需要"),
 "arch_bpf_stack_walk": (NOT, "BPF 异常支持专用，riscv 的 JIT 不支持 BPF 异常，公共层先判断再调用"),
 "pmdp_test_and_clear_young": (NOT, "工具误判：riscv 在透明大页配置下有自己的实现（调 ptep_test_and_clear_young），事实文件里没收录"),
 "flush_icache_pages": (NOT, "riscv 在 set_pte_at 里按 PG_dcache_clean 刷指令缓存，不靠这个钩子"),
 "gup_fast_permitted": (NOT, "x86、mips、s390 按地址宽度限制；riscv 的地址检查在别处，通用返回 true 合理"),
 "destroy_context": (NOT, "x86 要释放 LDT；riscv 的 init_new_context 不分配资源"),
 "flush_ptrace_hw_breakpoint": (NOT, "riscv 没有选 HAVE_HW_BREAKPOINT，空桩是设计如此"),
 "arch_probe_nr_irqs": (NOT, "按中断控制器探测中断数，riscv 用通用值"),
 "arch_enter_from_user_mode": (NOT, "x86、s390、powerpc 在这里做调试检查，riscv 不需要"),
 "copy_from_kernel_nofault_allowed": (UNK, "arm、loongarch、mips、powerpc、x86 都拒绝用户空间地址；riscv（和 arm64 一样）用通用的 true，靠 SUM 位让访问出错再由异常表兜底。功能上不出错，但语义与多数架构不同，需要专家判断"),
}
rows, cnt = [], collections.Counter()
items = {it["interface"]: (i + 1, it) for i, it in enumerate(d["top"])}
for k, n in enumerate(d["review_sample"], 1):
    v, why = R[n]
    cnt[v] += 1
    rank, it = items.get(n, (">300", None))
    q = it["q"] if it else "Q-类别"
    rows.append(f"| {k} | `{n}` | {rank} | {q} | {it['n_impl'] if it else ''} | {v} | {why} |")
prev = collections.Counter(d["prev_review"].values())
out = ["# 当前版本 riscv：40 个定性成立接口的人工核对（第二版）", "",
       f"定性成立 {d['by_q']['Q-多数'] + d['by_q']['Q-类别']} 个接口（Q-多数 {d['by_q']['Q-多数']}、Q-类别 {d['by_q']['Q-类别']}），"
       "按 Random(20261113) 抽 40 个。核对人 Claude，读 `/root/repos/linux`（7.3-rc2）。修订 2 之前的第一次抽样作废（只看过清单，没下判断）。", "",
       "结果：" + "，".join(f"{k} {v}" for k, v in cnt.most_common()) + "。", "",
       f"上一轮 40 条（23 个不同接口）在本轮的去向：{dict(prev)}（None 表示不再定性成立）。", "",
       "| # | 接口 | 排名 | 定性 | n_impl | 判断 | 理由 |", "|---|---|---|---|---|---|---|"] + rows
(HERE / "out/review_CUR_riscv.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print(dict(cnt), dict(prev))
