# 人工分析建议（第三版）：X1

Q-特性 14接口 9016 个；候选位置 20126 个，按接口聚合为 978 条；；Q-多数 23接口 9016 个；候选位置 20126 个，按接口聚合为 978 条；；Q-类别 26接口 9016 个；候选位置 20126 个，按接口聚合为 978 条；；none 795接口 9016 个；候选位置 20126 个，按接口聚合为 978 条；；特性专有 43接口 9016 个；候选位置 20126 个，按接口聚合为 978 条；；特性未开启 21接口 9016 个；候选位置 20126 个，按接口聚合为 978 条；；有意空实现 29接口 9016 个；候选位置 20126 个，按接口聚合为 978 条；；已判断 27。以下为前 50 条。

## 1. 接口 `arch_dup_mmap`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、powerpc、x86）
- 各架构实现：riscv generic include/asm-generic/mm_hooks.h:10 → none；arm64 arch arch/arm64/include/asm/mmu_context.h:185 → effect:mem（mem）；x86_64 arch arch/x86/include/asm/mmu_context.h:218 → effect（mem+pgtable+tlb）
- 可疑调用位置：`dup_mmap` mm/mmap.c:1842（F3，第 1847 行使用）；`dup_mmap` mm/mmap.c:1842（F3，第 1847 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、powerpc、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 9.0

## 2. 接口 `arch_prepare_to_swap`（Q-特性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 选了特性开关 CONFIG_MMU，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv generic include/linux/pgtable.h:1201 → none；arm64 arch arch/arm64/mm/mteswap.c:94 → effect:barrier+mem+register（barrier+mem+register）；x86_64 generic include/linux/pgtable.h:1451 → none
- 可疑调用位置：`swap_writeout` mm/page_io.c:251（F3，第 253 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 8.0

## 3. 接口 `arch_swap_invalidate_area`（Q-特性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 选了特性开关 CONFIG_MMU，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv generic include/linux/pgtable.h:1212 → none；arm64 arch arch/arm64/include/asm/pgtable.h:1561 → effect:mem（mem）；x86_64 generic include/linux/pgtable.h:1462 → none
- 可疑调用位置：`__do_sys_swapoff` mm/swapfile.c:2967（F3，第 2968 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 8.0

## 4. 接口 `arch_swap_invalidate_page`（Q-特性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 选了特性开关 CONFIG_MMU，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv generic include/linux/pgtable.h:1208 → none；arm64 arch arch/arm64/include/asm/pgtable.h:1555 → effect:mem（mem）；x86_64 generic include/linux/pgtable.h:1458 → none
- 可疑调用位置：`swap_range_free` mm/swapfile.c:1285（F3，第 1287 行使用）；`swap_range_free` mm/swapfile.c:1285（F3，第 1287 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 8.0

## 5. 接口 `exec_folio_order`（Q-特性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：riscv 选了特性开关 CONFIG_MMU，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv generic include/linux/pgtable.h:464 → none；arm64 无实现  → unknown；x86_64 generic include/linux/pgtable.h:618 → none
- 可疑调用位置：`do_sync_mmap_readahead` mm/filemap.c:3321（F2，第 3322 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 8.0

## 6. 接口 `mmap_upgrade_trylock`（Q-特性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 选了特性开关 CONFIG_LOCK_MM_AND_FIND_VMA、CONFIG_MMU，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv 无实现  → unknown；arm64 无实现  → unknown；x86_64 无实现  → unknown
- 可疑调用位置：`lock_mm_and_find_vma` mm/mmap_lock.c:453（F3，第 454 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、x86_64 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 8.0

## 7. 接口 `p4d_set_huge`（Q-特性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 选了特性开关 CONFIG_HAVE_ARCH_HUGE_VMAP，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv arch arch/riscv/mm/pgtable.c:63 → none；arm64 无实现  → unknown；x86_64 arch arch/x86/mm/pgtable.c:593 → none
- 可疑调用位置：`vmap_try_huge_p4d` mm/vmalloc.c:262（F3，第 262 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、x86_64 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 8.0

## 8. 接口 `arch_probe_nr_irqs`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm、loongarch、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 无实现  → unknown；x86_64 arch arch/x86/kernel/apic/vector.c:717 → effect
- 可疑调用位置：`early_irq_init` kernel/irq/irqdesc.c:557（F2，第 558 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、loongarch、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 9. 接口 `flush_anon_page`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（arm、csky、mips、parisc、sh）
- 各架构实现：riscv generic include/linux/highmem.h:186 → none；arm64 generic include/linux/highmem.h:186 → none；x86_64 generic include/linux/highmem.h:186 → none
- 可疑调用位置：`__get_user_pages` mm/gup.c:1499（F3，第 1500 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、csky、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 10. 接口 `flush_cache_dup_mm`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 9 个其他架构有实际实现（arm、csky、m68k、mips、nios2、parisc、sh、sparc）
- 各架构实现：riscv generic include/asm-generic/cacheflush.h:29 → none；arm64 generic include/asm-generic/cacheflush.h:29 → none；x86_64 generic include/asm-generic/cacheflush.h:29 → none
- 可疑调用位置：`dup_mmap` mm/mmap.c:1729（F3，第 1730 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、csky、m68k 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 11. 接口 `flush_cache_mm`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 8 个其他架构有实际实现（arm、csky、m68k、nios2、parisc、sh、sparc、xtensa）
- 各架构实现：riscv generic include/asm-generic/cacheflush.h:23 → none；arm64 generic include/asm-generic/cacheflush.h:23 → none；x86_64 generic include/asm-generic/cacheflush.h:23 → none
- 可疑调用位置：`exit_mmap` mm/mmap.c:1276（F3，第 1277 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、csky、m68k 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 12. 接口 `kvm_arch_flush_remote_tlbs`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、mips、x86）
- 各架构实现：riscv generic include/linux/kvm_host.h:1673 → none；arm64 arch arch/arm64/kvm/mmu.c:175 → effect:barrier+mem+tlb（barrier+mem+tlb）；x86_64 generic include/linux/kvm_host.h:1723 → none
- 可疑调用位置：`kvm_flush_remote_tlbs` virt/kvm/kvm_main.c:308（F3，第 309 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、mips、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 13. 接口 `kvm_arch_intc_initialized`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、loongarch、powerpc）
- 各架构实现：riscv generic include/linux/kvm_host.h:1741 → none；arm64 arch arch/arm64/kvm/arm.c:1006 → unknown；x86_64 generic include/linux/kvm_host.h:1791 → none
- 可疑调用位置：`kvm_irqfd_assign` virt/kvm/eventfd.c:365（F3，第 368 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 14. 接口 `kvm_arch_para_features`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（loongarch、powerpc、x86）
- 各架构实现：riscv generic include/asm-generic/kvm_para.h:17 → none；arm64 generic include/asm-generic/kvm_para.h:17 → none；x86_64 arch arch/x86/kernel/kvm.c:916 → effect（mem）
- 可疑调用位置：`kvm_para_has_feature` include/linux/kvm_para.h:10（F2，第 10 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 loongarch、powerpc、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 15. 接口 `arch_check_zapped_pte`（Q-特性，4 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 选了特性开关 CONFIG_MMU，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv generic include/linux/pgtable.h:471 → none；arm64 generic include/linux/pgtable.h:625 → none；x86_64 arch arch/x86/mm/pgtable.c:811 → unknown
- 可疑调用位置：`zap_present_folio_ptes` mm/memory.c:1645（F3，第 1647 行使用）；`zap_present_folio_ptes` mm/memory.c:1645（F3，第 1647 行使用）；`zap_present_ptes` mm/memory.c:1684（F3，第 1686 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 5.0474

## 16. 接口 `arch_unmap_one`（Q-特性，8 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 选了特性开关 CONFIG_MMU，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv generic include/linux/pgtable.h:1186 → none；arm64 generic include/linux/pgtable.h:1436 → none；x86_64 generic include/linux/pgtable.h:1436 → none
- 可疑调用位置：`try_to_unmap_one` mm/rmap.c:2172（F3，第 2174 行使用）；`try_to_unmap_one` mm/rmap.c:2172（F3，第 2226 行使用）；`try_to_unmap_one` mm/rmap.c:2172（F3，第 2174 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 sparc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 5.0474

## 17. 接口 `kvm_arch_disable_virtualization`（Q-特性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：riscv 选了特性开关 CONFIG_KVM_GENERIC_HARDWARE_ENABLING，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv 无实现  → unknown；arm64 无实现  → unknown；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_enable_virtualization` virt/kvm/kvm_main.c:5722（F2，第 5722 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 5.0474

## 18. 接口 `perf_reg_abi`（Q-特性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：riscv 选了特性开关 CONFIG_HAVE_PERF_REGS，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv arch arch/riscv/kernel/perf_regs.c:29 → none；arm64 arch arch/arm64/kernel/perf_regs.c:93 → effect；x86_64 arch arch/x86/kernel/perf_regs.c:123 → effect
- 可疑调用位置：`perf_sample_regs_user` kernel/events/core.c:7453（F2，第 7454 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 5.0474

## 19. 接口 `__tlb_remove_tlb_entry`（Q-特性，6 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 选了特性开关 CONFIG_MMU，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv generic include/asm-generic/tlb.h:628 → none；arm64 generic include/asm-generic/tlb.h:647 → none；x86_64 generic include/asm-generic/tlb.h:647 → none
- 可疑调用位置：`__unmap_hugepage_range` mm/hugetlb.c:5945（F3，第 5997 行使用）；`__unmap_hugepage_range` mm/hugetlb.c:5945（F3，第 5951 行使用）；`__unmap_hugepage_range` mm/hugetlb.c:5945（F3，第 5951 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 20. 接口 `arch_release_task_struct`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/kernel/process.c:193 → unknown；arm64 arch arch/arm64/kernel/process.c:344 → effect:mem（mem）；x86_64 arch arch/x86/kernel/process.c:118 → effect:mem（mem）
- 可疑调用位置：`free_task` kernel/fork.c:508（F3，第 509 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、s390、sh 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 21. 接口 `arch_swap_restore`（Q-特性，6 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 选了特性开关 CONFIG_MMU，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv generic include/linux/pgtable.h:1218 → none；arm64 arch arch/arm64/mm/mteswap.c:117 → effect:barrier+mem（barrier+mem）；x86_64 generic include/linux/pgtable.h:1468 → none
- 可疑调用位置：`do_swap_page` mm/memory.c:4909（F3，第 4916 行使用）；`do_swap_page` mm/memory.c:4909（F3，第 4917 行使用）；`shmem_swapin_folio` mm/shmem.c:2377（F3，第 2386 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 22. 接口 `arch_tlbbatch_flush`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 barrier 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/mm/tlbflush.c:237 → effect（mem+tlb）；arm64 arch arch/arm64/include/asm/tlbflush.h:403 → effect:barrier+tlb（barrier+tlb）；x86_64 arch arch/x86/mm/tlb.c:1682 → effect（barrier+mem+tlb）
- 可疑调用位置：`try_to_unmap_flush` mm/rmap.c:649（F3，第 650 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 23. 接口 `p4d_free`（Q-类别，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv generic include/asm-generic/pgalloc.h:257 → unknown；arm64 generic include/asm-generic/pgalloc.h:268 → effect:mem（mem）；x86_64 generic include/asm-generic/pgalloc.h:268 → effect:mem（mem）
- 可疑调用位置：`__p4d_alloc` mm/memory.c:6550（F3，第 6553 行使用）；`__p4d_alloc` mm/memory.c:6550（F3，第 6553 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 s390 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 24. 接口 `pte_unused`（Q-特性，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 选了特性开关 CONFIG_MMU，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv generic include/linux/pgtable.h:1085 → none；arm64 generic include/linux/pgtable.h:1335 → none；x86_64 generic include/linux/pgtable.h:1335 → none
- 可疑调用位置：`folio_unmap_pte_batch` mm/rmap.c:1856（F3，第 1859 行使用）；`try_to_unmap_one` mm/rmap.c:2091（F3，第 2142 行使用）；`try_to_migrate_one` mm/rmap.c:2482（F3，第 2504 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 s390 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 25. 接口 `pud_free`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/include/asm/pgalloc.h:83 → unknown；arm64 arch arch/arm64/include/asm/pgalloc.h:59 → effect:mem（mem）；x86_64 generic include/asm-generic/pgalloc.h:220 → effect:mem（mem）
- 可疑调用位置：`__pud_alloc` mm/memory.c:6577（F3，第 6578 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、powerpc、s390 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 26. 接口 `set_direct_map_invalid_noflush`（Q-类别，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 的实现缺少 mem、pgtable 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/mm/pageattr.c:377 → effect:tlb（tlb）；arm64 arch arch/arm64/mm/pageattr.c:254 → effect:mem+pgtable（mem+pgtable）；x86_64 arch arch/x86/mm/pat/set_memory.c:2659 → effect:mem+pgtable（mem+pgtable）
- 可疑调用位置：`secretmem_fault` mm/secretmem.c:75（F3，第 77 行使用）；`secretmem_fault` mm/secretmem.c:75（F2，第 78 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、s390 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 27. 接口 `set_memory_x`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 barrier、mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/mm/pageattr.c:367 → effect（tlb）；arm64 arch arch/arm64/mm/pageattr.c:235 → effect（barrier+mem+tlb）；x86_64 arch arch/x86/mm/pat/set_memory.c:2317 → effect（barrier+cache+mem+pgtable+tlb）
- 可疑调用位置：`set_memory_rox` include/linux/set_memory.h:23（F3，第 23 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、loongarch 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 28. 接口 `tlb_flush`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 barrier 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/include/asm/tlb.h:16 → effect:tlb（tlb）；arm64 arch arch/arm64/include/asm/tlb.h:53 → effect:barrier+tlb（barrier+tlb）；x86_64 arch arch/x86/include/asm/tlb.h:13 → effect（barrier+mem+tlb）
- 可疑调用位置：`tlb_flush_mmu_tlbonly` include/asm-generic/tlb.h:490（F3，第 491 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 29. 接口 `user_enable_single_step`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv generic include/linux/ptrace.h:287 → unknown；arm64 arch arch/arm64/kernel/debug-monitors.c:379 → effect（mem）；x86_64 arch arch/x86/kernel/step.c:219 → effect（mem）
- 可疑调用位置：`ptrace_resume` kernel/ptrace.c:848（F3，第 850 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 30. 接口 `wrprotect_ptes`（Q-类别，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem、pgtable 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv generic include/linux/pgtable.h:937 → unknown；arm64 arch arch/arm64/include/asm/pgtable.h:1902 → effect:mem+pgtable+tlb（mem+pgtable+tlb）；x86_64 generic include/linux/pgtable.h:1115 → effect:mem+pgtable（mem+pgtable）
- 可疑调用位置：`__copy_present_ptes` mm/memory.c:1089（F3，第 1101 行使用）；`__copy_present_ptes` mm/memory.c:1089（F3，第 1101 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 31. 接口 `destroy_context`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 11 个其他架构有实际实现（arc、m68k、microblaze、mips、openrisc、parisc、powerpc、sparc）
- 各架构实现：riscv generic include/asm-generic/mmu_context.h:46 → none；arm64 generic include/asm-generic/mmu_context.h:46 → none；x86_64 arch arch/x86/include/asm/mmu_context.h:172 → effect（mem）
- 可疑调用位置：`__mmdrop` kernel/fork.c:685（F3，第 686 行使用）；`mm_init` kernel/fork.c:1097（F3，第 1099 行使用）；`mm_init` kernel/fork.c:1097（F2，第 1097 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arc、m68k、microblaze 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.7856

## 32. 接口 `flush_icache_pages`（Q-多数，5 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（alpha、m68k、nios2、parisc、sh）
- 各架构实现：riscv generic include/linux/cacheflush.h:21 → none；arm64 generic include/linux/cacheflush.h:21 → none；x86_64 generic include/linux/cacheflush.h:21 → none
- 可疑调用位置：`do_swap_page` mm/memory.c:4947（F3，第 4952 行使用）；`do_swap_page` mm/memory.c:4947（F3，第 4965 行使用）；`do_swap_page` mm/memory.c:4947（F3，第 4965 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、m68k、nios2 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.7856

## 33. 接口 `flush_kernel_vmap_range`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（arm、csky、mips、parisc、sh）
- 各架构实现：riscv generic include/linux/highmem.h:192 → none；arm64 generic include/linux/highmem.h:192 → none；x86_64 generic include/linux/highmem.h:192 → none
- 可疑调用位置：`ring_buffer_map_get_reader` kernel/trace/ring_buffer.c:7405（F3，第 7408 行使用）；`ring_buffer_map_get_reader` kernel/trace/ring_buffer.c:7405（F3，第 7406 行使用）；`ring_buffer_map_get_reader` kernel/trace/ring_buffer.c:7405（F2，第 7405 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、csky、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.7856

## 34. 接口 `module_arch_cleanup`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 7 个其他架构有实际实现（arc、arm、mips、parisc、s390、sh、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 无实现  → unknown；x86_64 arch arch/x86/kernel/module.c:309 → effect:mem（mem）
- 可疑调用位置：`free_module` kernel/module/main.c:1405（F3，第 1408 行使用）；`load_module` kernel/module/main.c:3531（F3，第 3533 行使用）；`load_module` kernel/module/main.c:3531（F2，第 3531 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arc、arm、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.7856

## 35. 接口 `__arch_get_hw_counter`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/include/asm/vdso/gettimeofday.h:71 → unknown；arm64 arch arch/arm64/include/asm/vdso/gettimeofday.h:74 → unknown；x86_64 arch arch/x86/include/asm/vdso/gettimeofday.h:146 → unknown
- 可疑调用位置：`vdso_get_timestamp` lib/vdso/gettimeofday.c:101（F3，第 105 行使用）；`vdso_get_timestamp` lib/vdso/gettimeofday.c:101（F2，第 102 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、loongarch 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 36. 接口 `__cpu_up`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/smpboot.c:182 → effect:mem（mem）；arm64 arch arch/arm64/kernel/smp.c:113 → effect:barrier+mem（barrier+mem）；x86_64 无实现  → unknown
- 可疑调用位置：`bringup_cpu` kernel/cpu.c:879（F3，第 883 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arc、arm 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 37. 接口 `__get_wchan`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/stacktrace.c:168 → effect（mem）；arm64 arch arch/arm64/kernel/process.c:796 → effect（mem）；x86_64 arch arch/x86/kernel/process.c:1041 → effect（mem）
- 可疑调用位置：`get_wchan` kernel/sched/core.c:2074（F3，第 2075 行使用）；`get_wchan` kernel/sched/core.c:2074（F2，第 2077 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arc、arm 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 38. 接口 `arch_bpf_stack_walk`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、s390、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kernel/stacktrace.c:437 → effect:mem（mem）；x86_64 无实现  → unknown
- 可疑调用位置：`bpf_prog_find_from_stack` kernel/bpf/core.c:3314（F3，第 3315 行使用）；`bpf_throw` kernel/bpf/helpers.c:3025（F3，第 3026 行使用）；`bpf_stream_stage_dump_stack` kernel/bpf/stream.c:523（F3，第 524 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 39. 接口 `arch_dup_task_struct`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/process.c:200 → effect（mem）；arm64 arch arch/arm64/kernel/process.c:349 → effect（mem）；x86_64 arch arch/x86/kernel/process.c:105 → effect（mem）
- 可疑调用位置：`dup_task_struct` kernel/fork.c:877（F3，第 881 行使用）；`dup_task_struct` kernel/fork.c:877（F3，第 913 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 40. 接口 `arch_stack_walk`（Q-类别，4 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/kernel/stacktrace.c:179 → unknown；arm64 arch arch/arm64/kernel/stacktrace.c:381 → effect:mem（mem）；x86_64 arch arch/x86/kernel/stacktrace.c:15 → effect:mem（mem）
- 可疑调用位置：`stack_trace_save` kernel/stacktrace.c:122（F3，第 123 行使用）；`stack_trace_save_tsk` kernel/stacktrace.c:150（F3，第 152 行使用）；`stack_trace_save_tsk` kernel/stacktrace.c:150（F3，第 151 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、loongarch 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 41. 接口 `arch_thread_struct_whitelist`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/include/asm/processor.h:128 → effect（mem）；arm64 arch arch/arm64/include/asm/processor.h:269 → effect（mem）；x86_64 arch arch/x86/include/asm/processor.h:545 → effect（mem）
- 可疑调用位置：`task_struct_whitelist` kernel/fork.c:794（F3，第 801 行使用）；`task_struct_whitelist` kernel/fork.c:794（F3，第 800 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 42. 接口 `arch_uprobe_analyze_insn`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/probes/uprobes.c:31 → effect（mem）；arm64 无实现  → unknown；x86_64 arch arch/x86/kernel/uprobes.c:1626 → effect（mem）
- 可疑调用位置：`prepare_uprobe` kernel/events/uprobes.c:1117（F3，第 1122 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 43. 接口 `arch_uprobe_skip_sstep`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/probes/uprobes.c:91 → unknown；arm64 无实现  → unknown；x86_64 arch arch/x86/kernel/uprobes.c:1842 → unknown
- 可疑调用位置：`handle_swbp` kernel/events/uprobes.c:2778（F3，第 2781 行使用）；`handle_swbp` kernel/events/uprobes.c:2778（F3，第 2781 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 44. 接口 `arch_uretprobe_hijack_return_addr`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/probes/uprobes.c:130 → effect（mem）；arm64 无实现  → unknown；x86_64 arch arch/x86/kernel/uprobes.c:1851 → effect:mem（mem）
- 可疑调用位置：`prepare_uretprobe` kernel/events/uprobes.c:2267（F3，第 2273 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 45. 接口 `clock_getres_fallback`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/include/asm/vdso/gettimeofday.h:54 → effect；arm64 arch arch/arm64/include/asm/vdso/gettimeofday.h:58 → effect；x86_64 arch arch/x86/include/asm/vdso/gettimeofday.h:71 → effect
- 可疑调用位置：`__cvdso_clock_getres_data` lib/vdso/gettimeofday.c:476（F3，第 476 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、loongarch 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 46. 接口 `clock_gettime_fallback`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/include/asm/vdso/gettimeofday.h:38 → effect；arm64 arch arch/arm64/include/asm/vdso/gettimeofday.h:41 → effect；x86_64 arch arch/x86/include/asm/vdso/gettimeofday.h:58 → effect
- 可疑调用位置：`__cvdso_clock_gettime_data` lib/vdso/gettimeofday.c:325（F3，第 325 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、loongarch 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 47. 接口 `copy_thread`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/process.c:224 → effect（mem）；arm64 arch arch/arm64/kernel/process.c:413 → effect（mem）；x86_64 arch arch/x86/kernel/process.c:170 → effect（mem）
- 可疑调用位置：`copy_process` kernel/fork.c:2190（F3，第 2194 行使用）；`copy_process` kernel/fork.c:2190（F3，第 2197 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arc、arm 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 48. 接口 `flush_icache_range`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/include/asm/cacheflush.h:81 → effect:cache（cache）；arm64 arch arch/arm64/include/asm/cacheflush.h:84 → effect:barrier+cache+mem（barrier+cache+mem）；x86_64 generic include/asm-generic/cacheflush.h:71 → none
- 可疑调用位置：`flush_module_icache` kernel/module/main.c:2836（F3，第 2837 行使用）；`flush_module_icache` kernel/module/main.c:2836（F3，第 2837 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arc、arm 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 49. 接口 `futex_atomic_cmpxchg_inatomic`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/include/asm/futex.h:76 → effect（mem）；arm64 arch arch/arm64/include/asm/futex.h:285 → effect（mem）；x86_64 arch arch/x86/include/asm/futex.h:77 → effect（mem）
- 可疑调用位置：`futex_cmpxchg_value_locked` kernel/futex/futex.h:278（F2，第 281 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arc、arm 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 50. 接口 `huge_ptep_modify_prot_commit`（未定性，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv generic include/linux/hugetlb.h:1050 → effect（cache+mem+pgtable+tlb）；arm64 arch arch/arm64/mm/hugetlbpage.c:533 → effect（barrier+mem+pgtable+tlb）；x86_64 generic include/linux/hugetlb.h:1066 → effect（mem+pgtable）
- 可疑调用位置：`hugetlb_change_protection` mm/hugetlb.c:7214（F3，第 7236 行使用）；`hugetlb_change_protection` mm/hugetlb.c:7214（F3，第 7220 行使用）；`hugetlb_change_protection` mm/hugetlb.c:7214（F3，第 7220 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

