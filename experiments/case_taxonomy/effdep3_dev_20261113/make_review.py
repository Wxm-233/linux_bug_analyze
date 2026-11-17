"""out/review_CUR_riscv.md: Claude's manual judgements on the 40-interface review sample (effdep3 criteria 四)."""
import collections
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
d = json.load(open(HERE / "out/CUR_riscv.json", encoding="utf-8"))
NOT, UNK = "不是", "判断不了"
VIVT = (NOT, "只有虚拟索引缓存（VIVT）或有缓存别名的架构需要，设计如此", "VIVT")
MMU = (NOT, "守卫符号是 CONFIG_MMU（整个 pgtable.h 外层的大开关），不是这个接口的特性开关；实际是单个架构的专有特性", "MMU 开关误判")
MTE = (NOT, "arm64 MTE 标签专用，riscv 没有", "特性")
CB = (NOT, "工具误判：riscv 的实现经回调（页表遍历或栈回溯的回调函数）产生效果，闭包按函数名展开看不到", "回调")
VAL = (NOT, "工具误判：返回新值的页表项函数，riscv 实现里的 __pte/pte_val 等宏也算调用，J4 的纯值判断没生效", "纯值函数")
FEAT = lambda why: (NOT, why, "特性")
R = {
 "arch_check_zapped_pte": (NOT, "x86 影子栈检查；守卫是 CONFIG_MMU，误判", "MMU 开关误判"),
 "arch_prepare_to_swap": MTE, "arch_swap_invalidate_page": MTE, "arch_swap_invalidate_area": MTE,
 "__tlb_remove_tlb_entry": (NOT, "powerpc 哈希页表专用；守卫是 CONFIG_MMU，误判", "MMU 开关误判"),
 "exec_folio_order": (NOT, "arm64 对可执行文件页的预读优化，不是正确性要求；守卫是 CONFIG_MMU，误判", "MMU 开关误判"),
 "pte_batch_hint": (NOT, "arm64 连续页表项提示；守卫是 CONFIG_MMU，误判", "MMU 开关误判"),
 "arch_unmap_one": (NOT, "sparc ADI 专用；守卫是 CONFIG_MMU，误判", "MMU 开关误判"),
 "mmap_upgrade_trylock": (NOT, "mm/mmap_lock.c 里的静态函数，不是架构接口；守卫误判", "MMU 开关误判"),
 "Assert": (NOT, "名叫 Assert 的宏，不是架构接口", "工具"),
 "flush_anon_page": VIVT, "flush_cache_mm": VIVT, "flush_cache_page": VIVT, "flush_cache_vunmap": VIVT,
 "flush_dcache_mmap_unlock": VIVT, "flush_dcache_mmap_lock": VIVT, "flush_kernel_vmap_range": VIVT,
 "flush_cache_dup_mm": VIVT, "flush_cache_range": VIVT,
 "wrprotect_ptes": (NOT, "工具误判：riscv 用通用实现逐项调用 ptep_set_wrprotect（原子位操作），类别正则没认出是改页表", "工具"),
 "set_direct_map_default_noflush": CB, "set_direct_map_invalid_noflush": CB, "arch_stack_walk": CB, "show_stack": CB,
 "arch_dup_mmap": FEAT("x86 复制 LDT/pkey、arm64 复制 MTE/GCS 状态，riscv 没有"),
 "module_arch_freeing_init": FEAT("arm/parisc/s390 的模块私有数据"),
 "pte_wrprotect": VAL, "pte_mkold": VAL, "pte_modify": VAL, "pte_mkwrite": VAL, "huge_pte_mkuffd": VAL,
 "arch_enter_from_user_mode": FEAT("x86、s390、powerpc 的调试检查"),
 "arch_probe_nr_irqs": FEAT("按中断控制器探测中断数，riscv 用通用值"),
 "copy_from_kernel_nofault_allowed": (UNK, "多数架构拒绝用户空间地址；riscv（和 arm64 一样）用通用的 true，靠 SUM 位让访问出错再由异常表兜底，语义不同，需要专家判断", "判断不了"),
 "memory_block_size_bytes": FEAT("x86、powerpc、s390 按固件信息计算内存块大小，riscv 用默认值合理"),
 "arch_release_task_struct": (NOT, "工具误判：riscv 在这里释放向量上下文（riscv_v_thread_free），只是调用名不在类别里", "工具"),
 "destroy_context": FEAT("x86 释放 LDT；riscv 不分配"),
 "kvm_arch_para_features": FEAT("KVM 客户机半虚拟化，riscv 客户机走 SBI"),
 "tlb_flush": (NOT, "工具判 riscv 缺屏障；sfence.vma 本身对页表访问排序，架构语义不同", "工具"),
 "enter_lazy_tlb": FEAT("惰性 TLB 状态优化，riscv 不需要"),
}
rows, cnt, why_cnt = [], collections.Counter(), collections.Counter()
items = {it["interface"]: (i + 1, it) for i, it in enumerate(d["top"])}
for k, n in enumerate(d["review_sample"], 1):
    v, why, cat = R[n]
    cnt[v] += 1
    why_cnt[cat] += 1
    rank, it = items.get(n, (">300", None))
    rows.append(f"| {k} | `{n}` | {rank} | {it['q'] if it else 'Q-类别'} | {'、'.join(it['gate'] or []) if it else ''} | {v} | {why} |")
prev = collections.Counter(d["prev_review"].values())
qual = d["by_q"]["Q-特性"] + d["by_q"]["Q-多数"] + d["by_q"]["Q-类别"]
out = ["# 当前版本 riscv：40 个定性成立接口的人工核对（第三版）", "",
       f"定性成立 {qual} 个接口（Q-特性 {d['by_q']['Q-特性']}、Q-多数 {d['by_q']['Q-多数']}、Q-类别 {d['by_q']['Q-类别']}），"
       "按 Random(20261113) 抽 40 个。核对人 Claude。", "",
       "结果：" + "，".join(f"{k} {v}" for k, v in cnt.most_common()) + "。按原因：" + "，".join(f"{k} {v}" for k, v in why_cnt.most_common()) + "。", "",
       f"第二版核对过的 40 个接口在本轮的去向：{dict(prev)}。", "",
       "| # | 接口 | 排名 | 定性 | 守卫符号 | 判断 | 理由 |", "|---|---|---|---|---|---|---|"] + rows
(HERE / "out/review_CUR_riscv.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print(dict(cnt), dict(why_cnt), dict(prev))
