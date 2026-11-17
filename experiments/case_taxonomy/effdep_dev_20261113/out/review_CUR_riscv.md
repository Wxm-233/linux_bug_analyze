# 当前版本 riscv：40 条定性成立候选的人工核对

抽样：定性成立 53 条中按 Random(20261113) 抽 40 条（判据第八节第 3 条）。核对人：Claude，读的是 `/root/repos/linux`（7.3-rc2）源码。

结果：不是 38 条，疑似真问题 2 条。疑似真问题的 2 条是同一个根因（`syscall_get_arch`），按根因算 1 个。按规则不对外报告。

| # | 位置 | 接口 | 形态 | 横向比对 | 判断 | 理由 |
|---|---|---|---|---|---|---|
| 1 | `should_defer_flush` mm/rmap.c:792 | `arch_tlbbatch_should_defer` | F3 | riscv none；arm64 none；x86_64 effect | 不是 | 批量刷 TLB 的延迟优化只有 x86 实现；riscv 返回 false 只是不启用优化 |
| 2 | `perf_misc_flags` kernel/events/core.c:7797 | `perf_arch_guest_misc_flags` | F3 | riscv none；arm64 none；x86_64 effect | 不是 | 只有 x86 提供客户机 perf 标志 |
| 3 | `ptrace_detach` kernel/ptrace.c:595 | `ptrace_disable` | F3 | riscv none；arm64 effect；x86_64 effect | 不是 | arm64、x86 在这里关硬件单步；riscv 没有硬件单步，空实现是设计如此 |
| 4 | `free_huge_folio` mm/hugetlb.c:1735 | `arch_clear_hugetlb_flags` | F3 | riscv effect；arm64 effect；x86_64 none | 不是 | 只有带架构私有页标志的架构需要清；x86 没有这类标志 |
| 5 | `sg_miter_stop` lib/scatterlist.c:937 | `flush_dcache_page` | F3 | riscv effect；arm64 effect；x86_64 none | 不是 | x86 的数据缓存与指令/DMA 一致，不需要刷数据缓存，空实现是设计如此 |
| 6 | `kprobe_page_fault` include/linux/kprobes.h:592 | `kprobe_fault_handler` | F3 | riscv none；arm64 none；x86_64 effect | 不是 | 通用实现是 kprobes 未用时的返回 0；riscv 实现在 arch/riscv/kernel/probes 中，默认配置的范围内未看到，属抽取范围问题，不是缺陷 |
| 7 | `__audit_syscall_entry` kernel/auditsc.c:2013 | `syscall_get_arch` | F2 | riscv none；arm64 none；x86_64 effect | 疑似真问题 | riscv64 默认开 COMPAT（32 位用户态），但 syscall_get_arch 对 32 位任务也返回 AUDIT_ARCH_RISCV64，seccomp.h 也没有定义 SECCOMP_ARCH_COMPAT；arm64 会区分 compat 任务。审计记录和 seccomp 过滤器可能把 32 位任务当成 64 位。工具把 arm64 判成“无效果”是摘要误判（它依赖任务），但指向的差异是真的 |
| 8 | `cpc_write` drivers/acpi/cppc_acpi.c:1237 | `cpc_write_ffh` | F3 | riscv unknown；arm64 none；x86_64 effect | 不是 | FFH 寄存器写各架构按需实现，arm64 不支持返回 -EOPNOTSUPP 是设计如此 |
| 9 | `insert_page_into_pte_locked` mm/memory.c:2500 | `ptep_set_access_flags` | F3 | riscv none；arm64 effect；x86_64 unknown | 不是 | 资源是按值传入的 entry，“产生效果”对按值参数没有意义；riscv 实际写了 ptep。工具误判 |
| 10 | `shmem_get_folio_gfp` mm/shmem.c:2579 | `flush_dcache_folio` | F3 | riscv effect；arm64 effect；x86_64 none | 不是 | x86 的数据缓存与指令/DMA 一致，不需要刷数据缓存，空实现是设计如此 |
| 11 | `hypervisor_isolated_pci_functions` include/linux/hypervisor.h:43 | `jailhouse_paravirt` | F3 | riscv effect；arm64 effect；x86_64 none | 不是 | Jailhouse 只支持 x86，x86 侧返回 false 是对的 |
| 12 | `dup_mmap` mm/mmap.c:1827 | `arch_dup_mmap` | F3 | riscv none；arm64 effect；x86_64 effect | 不是 | x86 复制 LDT/pkey，arm64 复制 MTE/GCS 状态；riscv 没有这些状态 |
| 13 | `unuse_pte` mm/swapfile.c:2477 | `arch_swap_restore` | F3 | riscv none；arm64 effect；x86_64 none | 不是 | 只用于 arm64 MTE 标签恢复，其他架构没有标签 |
| 14 | `shmem_file_read_iter` mm/shmem.c:3375 | `flush_dcache_page` | F3 | riscv effect；arm64 effect；x86_64 none | 不是 | x86 的数据缓存与指令/DMA 一致，不需要刷数据缓存，空实现是设计如此 |
| 15 | `folio_pte_batch_flags` kernel/../mm/internal.h:451 | `pte_batch_hint` | F2 | riscv none；arm64 effect；x86_64 none | 不是 | 只有 arm64 有连续页表项（contpte）提示；通用实现返回 1 是正确的保守值 |
| 16 | `resilient_queued_spin_lock_slowpath` kernel/bpf/rqspinlock.c:349 | `resilient_virt_spin_lock` | F3 | riscv none；arm64 none；x86_64 effect | 不是 | 只有 x86 有虚拟化下的自旋锁回退 |
| 17 | `mm_init` kernel/fork.c:1159 | `destroy_context` | F3 | riscv none；arm64 none；x86_64 effect | 不是 | x86 要释放 LDT；riscv 的 init_new_context 不分配资源，无需释放 |
| 18 | `shmem_file_read_iter` mm/shmem.c:3373 | `flush_dcache_folio` | F3 | riscv effect；arm64 effect；x86_64 none | 不是 | x86 的数据缓存与指令/DMA 一致，不需要刷数据缓存，空实现是设计如此 |
| 19 | `folio_pte_batch_flags` lib/../mm/internal.h:434 | `pte_batch_hint` | F2 | riscv none；arm64 effect；x86_64 none | 不是 | 只有 arm64 有连续页表项（contpte）提示；通用实现返回 1 是正确的保守值 |
| 20 | `force_sig_seccomp` kernel/signal.c:1820 | `syscall_get_arch` | F2 | riscv none；arm64 none；x86_64 effect | 疑似真问题 | riscv64 默认开 COMPAT（32 位用户态），但 syscall_get_arch 对 32 位任务也返回 AUDIT_ARCH_RISCV64，seccomp.h 也没有定义 SECCOMP_ARCH_COMPAT；arm64 会区分 compat 任务。审计记录和 seccomp 过滤器可能把 32 位任务当成 64 位。工具把 arm64 判成“无效果”是摘要误判（它依赖任务），但指向的差异是真的 |
| 21 | `generic_perform_write` mm/filemap.c:4393 | `flush_dcache_folio` | F3 | riscv effect；arm64 effect；x86_64 none | 不是 | x86 的数据缓存与指令/DMA 一致，不需要刷数据缓存，空实现是设计如此 |
| 22 | `folio_pte_batch_flags` kernel/../mm/internal.h:434 | `pte_batch_hint` | F2 | riscv none；arm64 effect；x86_64 none | 不是 | 只有 arm64 有连续页表项（contpte）提示；通用实现返回 1 是正确的保守值 |
| 23 | `perf_copy_attr` kernel/events/core.c:13712 | `perf_reg_validate` | F2 | riscv none；arm64 effect；x86_64 none | 不是 | riscv 按掩码返回 -EINVAL 或 0，依赖输入；摘要把“只返回常量”误当成无效果 |
| 24 | `add_hugetlb_folio` mm/hugetlb.c:1443 | `arch_clear_hugetlb_flags` | F3 | riscv effect；arm64 effect；x86_64 none | 不是 | 只有带架构私有页标志的架构需要清；x86 没有这类标志 |
| 25 | `ptrace_resume` kernel/ptrace.c:876 | `user_disable_single_step` | F3 | riscv none；arm64 effect；x86_64 effect | 不是 | riscv 没有用户态硬件单步，通用空实现是设计如此 |
| 26 | `array_map_mmap_fault` kernel/bpf/arraymap.c:643 | `flush_dcache_folio` | F3 | riscv effect；arm64 effect；x86_64 none | 不是 | x86 的数据缓存与指令/DMA 一致，不需要刷数据缓存，空实现是设计如此 |
| 27 | `shmem_writeout` mm/shmem.c:1692 | `flush_dcache_folio` | F3 | riscv effect；arm64 effect；x86_64 none | 不是 | x86 的数据缓存与指令/DMA 一致，不需要刷数据缓存，空实现是设计如此 |
| 28 | `folio_pte_batch_flags` mm/internal.h:434 | `pte_batch_hint` | F2 | riscv none；arm64 effect；x86_64 none | 不是 | 只有 arm64 有连续页表项（contpte）提示；通用实现返回 1 是正确的保守值 |
| 29 | `is_kernel` include/linux/kallsyms.h:38 | `in_gate_area_no_mm` | F3 | riscv none；arm64 none；x86_64 effect | 不是 | 只有 x86 有 vsyscall 页 |
| 30 | `copy_process` kernel/fork.c:2374 | `user_disable_single_step` | F3 | riscv none；arm64 effect；x86_64 effect | 不是 | riscv 没有用户态硬件单步，通用空实现是设计如此 |
| 31 | `do_mmap` mm/mmap.c:395 | `execute_only_pkey` | F3 | riscv unknown；arm64 none；x86_64 effect | 不是 | 只有支持保护键的架构有效果 |
| 32 | `update_vsyscall` kernel/time/vsyscall.c:121 | `__arch_update_vdso_clock` | F3 | riscv none；arm64 effect；x86_64 none | 不是 | 只有 arm64 需要在 vDSO 数据里补架构字段 |
| 33 | `__clocksource_register_scale` kernel/time/clocksource.c:1299 | `clocksource_arch_init` | F3 | riscv none；arm64 none；x86_64 effect | 不是 | x86 在这里校验 vDSO 时钟模式，其他架构用通用空实现，设计如此 |
| 34 | `filemap_splice_read` mm/filemap.c:3140 | `flush_dcache_folio` | F3 | riscv effect；arm64 effect；x86_64 none | 不是 | x86 的数据缓存与指令/DMA 一致，不需要刷数据缓存，空实现是设计如此 |
| 35 | `hugepage_migration_supported` include/linux/hugetlb.h:917 | `arch_hugetlb_migration_supported` | F3 | riscv effect；arm64 effect；x86_64 none | 不是 | x86 用通用默认，按页大小判断可迁移性，设计如此 |
| 36 | `dup_mmap` mm/mmap.c:1827 | `arch_dup_mmap` | F3 | riscv none；arm64 unknown；x86_64 effect | 不是 | x86 复制 LDT/pkey，arm64 复制 MTE/GCS 状态；riscv 没有这些状态 |
| 37 | `shmem_file_splice_read` mm/shmem.c:3568 | `flush_dcache_folio` | F3 | riscv effect；arm64 effect；x86_64 none | 不是 | x86 的数据缓存与指令/DMA 一致，不需要刷数据缓存，空实现是设计如此 |
| 38 | `do_swap_page` mm/memory.c:5159 | `arch_swap_restore` | F3 | riscv none；arm64 effect；x86_64 none | 不是 | 只用于 arm64 MTE 标签恢复，其他架构没有标签 |
| 39 | `shmem_replace_folio` mm/shmem.c:2118 | `flush_dcache_folio` | F3 | riscv effect；arm64 effect；x86_64 none | 不是 | x86 的数据缓存与指令/DMA 一致，不需要刷数据缓存，空实现是设计如此 |
| 40 | `is_kernel_text` include/linux/kallsyms.h:31 | `in_gate_area_no_mm` | F3 | riscv none；arm64 none；x86_64 effect | 不是 | 只有 x86 有 vsyscall 页 |
