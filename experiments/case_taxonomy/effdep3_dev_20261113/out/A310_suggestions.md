# 人工分析建议（第三版）：A310

Q-特性 15接口 8019 个；候选位置 18957 个，按接口聚合为 918 条；；Q-多数 18接口 8019 个；候选位置 18957 个，按接口聚合为 918 条；；Q-类别 24接口 8019 个；候选位置 18957 个，按接口聚合为 918 条；；none 747接口 8019 个；候选位置 18957 个，按接口聚合为 918 条；；特性专有 66接口 8019 个；候选位置 18957 个，按接口聚合为 918 条；；特性未开启 22接口 8019 个；候选位置 18957 个，按接口聚合为 918 条；；有意空实现 21接口 8019 个；候选位置 18957 个，按接口聚合为 918 条；；已判断 5。以下为前 50 条。

## 1. 接口 `pgd_devmap`（Q-特性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 选了特性开关 CONFIG_ARCH_HAS_PTE_DEVMAP、CONFIG_MMU，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv generic include/linux/pgtable.h:1622 → none；arm64 无实现  → unknown；x86_64 无实现  → unknown
- 可疑调用位置：`gup_fast_pgd_leaf` mm/gup.c:3152（F3，第 3154 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、x86_64 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 12.0

## 2. 接口 `kvm_arch_create_vm_debugfs`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、powerpc、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kvm/arm.c:295 → unknown；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_create_vm_debugfs` virt/kvm/kvm_main.c:1107（F3，第 1110 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、powerpc、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 9.0

## 3. 接口 `arch_prepare_to_swap`（Q-特性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 选了特性开关 CONFIG_MMU，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv generic include/linux/pgtable.h:1147 → none；arm64 arch arch/arm64/mm/mteswap.c:94 → effect:barrier+mem+register（barrier+mem+register）；x86_64 generic include/linux/pgtable.h:1451 → none
- 可疑调用位置：`swap_writepage` mm/page_io.c:192（F3，第 194 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 8.0

## 4. 接口 `arch_swap_invalidate_area`（Q-特性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 选了特性开关 CONFIG_MMU，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv generic include/linux/pgtable.h:1158 → none；arm64 arch arch/arm64/include/asm/pgtable.h:1561 → effect:mem（mem）；x86_64 generic include/linux/pgtable.h:1462 → none
- 可疑调用位置：`__do_sys_swapoff` mm/swapfile.c:2640（F3，第 2641 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 8.0

## 5. 接口 `arch_swap_invalidate_page`（Q-特性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 选了特性开关 CONFIG_MMU，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv generic include/linux/pgtable.h:1154 → none；arm64 arch arch/arm64/include/asm/pgtable.h:1555 → effect:mem（mem）；x86_64 generic include/linux/pgtable.h:1458 → none
- 可疑调用位置：`swap_range_free` mm/swapfile.c:766（F3，第 768 行使用）；`swap_range_free` mm/swapfile.c:766（F3，第 768 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 8.0

## 6. 接口 `p4d_set_huge`（Q-特性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 选了特性开关 CONFIG_HAVE_ARCH_HUGE_VMAP，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv arch arch/riscv/mm/pgtable.c:50 → none；arm64 无实现  → unknown；x86_64 arch arch/x86/mm/pgtable.c:593 → none
- 可疑调用位置：`vmap_try_huge_p4d` mm/vmalloc.c:257（F3，第 257 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、x86_64 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 8.0

## 7. 接口 `pte_needs_flush`（Q-特性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 选了特性开关 CONFIG_MMU，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv generic include/asm-generic/tlb.h:738 → none；arm64 arch arch/arm64/include/asm/tlbflush.h:709 → unknown；x86_64 arch arch/x86/include/asm/tlbflush.h:445 → unknown
- 可疑调用位置：`change_pte_range` mm/mprotect.c:197（F3，第 200 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 parisc、powerpc、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 8.0

## 8. 接口 `arch_bpf_stack_walk`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、s390、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kernel/stacktrace.c:437 → effect:mem（mem）；x86_64 无实现  → unknown
- 可疑调用位置：`bpf_throw` kernel/bpf/helpers.c:2755（F3，第 2756 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 9. 接口 `arch_prctl_spec_ctrl_get`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、powerpc、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kernel/proton-pack.c:798 → unknown；x86_64 arch arch/x86/kernel/cpu/bugs.c:2735 → unknown
- 可疑调用位置：`__do_sys_prctl` kernel/sys.c:2668（F3，第 2673 行使用）；`__do_sys_prctl` kernel/sys.c:2668（F3，第 2673 行使用）；`__do_sys_prctl` kernel/sys.c:2668（F2，第 2789 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、powerpc、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 10. 接口 `arch_vma_name`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 6 个其他架构有实际实现（arm、csky、hexagon、nios2、sh、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 无实现  → unknown；x86_64 无实现  → unknown
- 可疑调用位置：`perf_event_mmap_event` kernel/events/core.c:8815（F3，第 8817 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、csky、hexagon 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 11. 接口 `flush_anon_page`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（arm、csky、mips、parisc、sh）
- 各架构实现：riscv generic include/linux/highmem.h:186 → none；arm64 generic include/linux/highmem.h:186 → none；x86_64 generic include/linux/highmem.h:186 → none
- 可疑调用位置：`__get_user_pages` mm/gup.c:1565（F3，第 1566 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、csky、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 12. 接口 `flush_cache_dup_mm`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 9 个其他架构有实际实现（arm、csky、m68k、mips、nios2、parisc、sh、sparc）
- 各架构实现：riscv generic include/asm-generic/cacheflush.h:29 → none；arm64 generic include/asm-generic/cacheflush.h:29 → none；x86_64 generic include/asm-generic/cacheflush.h:29 → none
- 可疑调用位置：`dup_mmap` kernel/fork.c:640（F3，第 641 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、csky、m68k 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 13. 接口 `flush_cache_mm`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 8 个其他架构有实际实现（arm、csky、m68k、nios2、parisc、sh、sparc、xtensa）
- 各架构实现：riscv generic include/asm-generic/cacheflush.h:23 → none；arm64 generic include/asm-generic/cacheflush.h:23 → none；x86_64 generic include/asm-generic/cacheflush.h:23 → none
- 可疑调用位置：`exit_mmap` mm/mmap.c:3408（F3，第 3409 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、csky、m68k 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 14. 接口 `kvm_arch_flush_remote_tlbs`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、mips、x86）
- 各架构实现：riscv generic include/linux/kvm_host.h:1554 → none；arm64 arch arch/arm64/kvm/mmu.c:175 → effect:barrier+mem+tlb（barrier+mem+tlb）；x86_64 generic include/linux/kvm_host.h:1723 → none
- 可疑调用位置：`kvm_flush_remote_tlbs` virt/kvm/kvm_main.c:349（F3，第 350 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、mips、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 15. 接口 `arch_check_zapped_pte`（Q-特性，4 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 选了特性开关 CONFIG_MMU，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv generic include/linux/pgtable.h:437 → none；arm64 generic include/linux/pgtable.h:625 → none；x86_64 arch arch/x86/mm/pgtable.c:811 → unknown
- 可疑调用位置：`zap_present_folio_ptes` mm/memory.c:1510（F3，第 1512 行使用）；`zap_present_folio_ptes` mm/memory.c:1510（F3，第 1512 行使用）；`zap_present_ptes` mm/memory.c:1550（F3，第 1552 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 5.0474

## 16. 接口 `arch_unmap_one`（Q-特性，8 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 选了特性开关 CONFIG_MMU，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv generic include/linux/pgtable.h:1132 → none；arm64 generic include/linux/pgtable.h:1436 → none；x86_64 generic include/linux/pgtable.h:1436 → none
- 可疑调用位置：`try_to_unmap_one` mm/rmap.c:1884（F3，第 1886 行使用）；`try_to_unmap_one` mm/rmap.c:1884（F3，第 1931 行使用）；`try_to_unmap_one` mm/rmap.c:1884（F3，第 1886 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 sparc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 5.0474

## 17. 接口 `perf_reg_abi`（Q-特性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：riscv 选了特性开关 CONFIG_HAVE_PERF_REGS，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv arch arch/riscv/kernel/perf_regs.c:29 → none；arm64 arch arch/arm64/kernel/perf_regs.c:93 → effect；x86_64 arch arch/x86/kernel/perf_regs.c:123 → effect
- 可疑调用位置：`perf_sample_regs_user` kernel/events/core.c:6938（F2，第 6939 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 5.0474

## 18. 接口 `pte_unused`（Q-特性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 选了特性开关 CONFIG_MMU，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv generic include/linux/pgtable.h:993 → none；arm64 generic include/linux/pgtable.h:1335 → none；x86_64 generic include/linux/pgtable.h:1335 → none
- 可疑调用位置：`try_to_unmap_one` mm/rmap.c:1805（F3，第 1870 行使用）；`try_to_migrate_one` mm/rmap.c:2213（F3，第 2229 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 s390 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 5.0474

## 19. 接口 `__tlb_remove_tlb_entry`（Q-特性，6 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 选了特性开关 CONFIG_MMU，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv generic include/asm-generic/tlb.h:603 → none；arm64 generic include/asm-generic/tlb.h:647 → none；x86_64 generic include/asm-generic/tlb.h:647 → none
- 可疑调用位置：`__unmap_hugepage_range` mm/hugetlb.c:5711（F3，第 5760 行使用）；`__unmap_hugepage_range` mm/hugetlb.c:5711（F3，第 5717 行使用）；`__unmap_hugepage_range` mm/hugetlb.c:5711（F3，第 5717 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 20. 接口 `arch_release_task_struct`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/kernel/process.c:176 → unknown；arm64 arch arch/arm64/kernel/process.c:344 → effect:mem（mem）；x86_64 arch arch/x86/kernel/process.c:118 → effect:mem（mem）
- 可疑调用位置：`free_task` kernel/fork.c:609（F3，第 610 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、s390、sh 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 21. 接口 `arch_swap_restore`（Q-特性，6 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 选了特性开关 CONFIG_MMU，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv generic include/linux/pgtable.h:1164 → none；arm64 arch arch/arm64/mm/mteswap.c:117 → effect:barrier+mem（barrier+mem）；x86_64 generic include/linux/pgtable.h:1468 → none
- 可疑调用位置：`do_swap_page` mm/memory.c:4296（F3，第 4303 行使用）；`do_swap_page` mm/memory.c:4296（F3，第 4304 行使用）；`shmem_swapin_folio` mm/shmem.c:2035（F3，第 2044 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 22. 接口 `arch_tlbbatch_flush`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 barrier 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/mm/tlbflush.c:200 → effect（mem+tlb）；arm64 arch arch/arm64/include/asm/tlbflush.h:403 → effect:barrier+tlb（barrier+tlb）；x86_64 arch arch/x86/mm/tlb.c:1682 → effect（barrier+mem+tlb）
- 可疑调用位置：`try_to_unmap_flush` mm/rmap.c:650（F3，第 651 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 23. 接口 `huge_pte_modify`（Q-类别，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 的实现缺少 mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv generic include/asm-generic/hugetlb.h:40 → unknown；arm64 generic include/asm-generic/hugetlb.h:35 → effect（mem）；x86_64 generic include/asm-generic/hugetlb.h:35 → effect（mem+pgtable）
- 可疑调用位置：`hugetlb_change_protection` mm/hugetlb.c:6969（F3，第 6975 行使用）；`hugetlb_change_protection` mm/hugetlb.c:6969（F2，第 6970 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 s390 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 24. 接口 `set_direct_map_invalid_noflush`（Q-类别，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 的实现缺少 pgtable 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/mm/pageattr.c:377 → effect:mem+tlb（mem+tlb）；arm64 arch arch/arm64/mm/pageattr.c:254 → effect:mem+pgtable（mem+pgtable）；x86_64 arch arch/x86/mm/pat/set_memory.c:2659 → effect:mem+pgtable（mem+pgtable）
- 可疑调用位置：`secretmem_fault` mm/secretmem.c:77（F3，第 93 行使用）；`secretmem_fault` mm/secretmem.c:77（F2，第 80 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 25. 接口 `set_memory_x`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 barrier 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/mm/pageattr.c:367 → effect（mem+tlb）；arm64 arch arch/arm64/mm/pageattr.c:235 → effect（barrier+mem+tlb）；x86_64 arch arch/x86/mm/pat/set_memory.c:2317 → effect（barrier+cache+mem+pgtable+tlb）
- 可疑调用位置：`set_memory_rox` include/linux/set_memory.h:23（F3，第 23 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 26. 接口 `tlb_flush`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 barrier 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/include/asm/tlb.h:34 → effect:tlb（tlb）；arm64 arch arch/arm64/include/asm/tlb.h:53 → effect:barrier+tlb（barrier+tlb）；x86_64 arch arch/x86/include/asm/tlb.h:13 → effect（barrier+mem+tlb）
- 可疑调用位置：`tlb_flush_mmu_tlbonly` include/asm-generic/tlb.h:465（F3，第 466 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 27. 接口 `user_enable_single_step`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv generic include/linux/ptrace.h:287 → unknown；arm64 arch arch/arm64/kernel/debug-monitors.c:379 → effect（mem）；x86_64 arch arch/x86/kernel/step.c:219 → effect（mem）
- 可疑调用位置：`ptrace_resume` kernel/ptrace.c:848（F3，第 850 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 28. 接口 `wrprotect_ptes`（Q-类别，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem、pgtable 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv generic include/linux/pgtable.h:845 → unknown；arm64 arch arch/arm64/include/asm/pgtable.h:1902 → effect:mem+pgtable+tlb（mem+pgtable+tlb）；x86_64 generic include/linux/pgtable.h:1115 → effect:mem+pgtable（mem+pgtable）
- 可疑调用位置：`__copy_present_ptes` mm/memory.c:955（F3，第 967 行使用）；`__copy_present_ptes` mm/memory.c:955（F3，第 967 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 29. 接口 `flush_icache_pages`（Q-多数，5 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（alpha、m68k、nios2、parisc、sh）
- 各架构实现：riscv generic include/linux/cacheflush.h:21 → none；arm64 generic include/linux/cacheflush.h:21 → none；x86_64 generic include/linux/cacheflush.h:21 → none
- 可疑调用位置：`do_swap_page` mm/memory.c:4334（F3，第 4339 行使用）；`do_swap_page` mm/memory.c:4334（F3，第 4351 行使用）；`do_swap_page` mm/memory.c:4334（F3，第 4351 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、m68k、nios2 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.7856

## 30. 接口 `module_arch_cleanup`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 7 个其他架构有实际实现（arc、arm、mips、parisc、s390、sh、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 无实现  → unknown；x86_64 arch arch/x86/kernel/module.c:309 → effect:mem（mem）
- 可疑调用位置：`free_module` kernel/module/main.c:1281（F3，第 1284 行使用）；`load_module` kernel/module/main.c:3031（F3，第 3033 行使用）；`load_module` kernel/module/main.c:3031（F2，第 3031 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arc、arm、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.7856

## 31. 接口 `pte_batch_hint`（Q-特性，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 选了特性开关 CONFIG_MMU，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv generic include/linux/pgtable.h:230 → none；arm64 arch arch/arm64/include/asm/pgtable.h:1712 → unknown；x86_64 generic include/linux/pgtable.h:410 → none
- 可疑调用位置：`folio_pte_batch` mm/internal.h:173（F3，第 174 行使用）；`folio_pte_batch` mm/internal.h:173（F2，第 174 行使用）；`folio_pte_batch` mm/internal.h:205（F2，第 206 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.4454

## 32. 接口 `pud_trans_huge`（Q-特性，4 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 选了特性开关 CONFIG_MMU，却没有自己的实现（通用桩是空的）
- 各架构实现：riscv generic include/linux/pgtable.h:1630 → none；arm64 generic include/linux/pgtable.h:2091 → none；x86_64 generic include/linux/pgtable.h:2091 → none
- 可疑调用位置：`copy_pud_range` mm/memory.c:1275（F3，第 1280 行使用）；`zap_pud_range` mm/memory.c:1755（F3，第 1759 行使用）；`__handle_mm_fault` mm/memory.c:5608（F3，第 5614 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 powerpc、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.4454

## 33. 接口 `__cpu_up`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/smpboot.c:182 → effect:mem（mem）；arm64 arch arch/arm64/kernel/smp.c:113 → effect:barrier+mem（barrier+mem）；x86_64 无实现  → unknown
- 可疑调用位置：`bringup_cpu` kernel/cpu.c:877（F3，第 881 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arc、arm 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 34. 接口 `__get_wchan`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/stacktrace.c:149 → effect（mem）；arm64 arch arch/arm64/kernel/process.c:796 → effect（mem）；x86_64 arch arch/x86/kernel/process.c:1041 → effect（mem）
- 可疑调用位置：`get_wchan` kernel/sched/core.c:1962（F3，第 1963 行使用）；`get_wchan` kernel/sched/core.c:1962（F2，第 1965 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arc、arm 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 35. 接口 `arch_dup_task_struct`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/process.c:183 → effect（mem）；arm64 arch arch/arm64/kernel/process.c:349 → effect（mem）；x86_64 arch arch/x86/kernel/process.c:105 → effect（mem）
- 可疑调用位置：`dup_task_struct` kernel/fork.c:1109（F3，第 1113 行使用）；`dup_task_struct` kernel/fork.c:1109（F3，第 1145 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 36. 接口 `arch_stack_walk`（Q-类别，4 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/kernel/stacktrace.c:160 → unknown；arm64 arch arch/arm64/kernel/stacktrace.c:381 → effect:mem（mem）；x86_64 arch arch/x86/kernel/stacktrace.c:15 → effect:mem（mem）
- 可疑调用位置：`stack_trace_save` kernel/stacktrace.c:122（F3，第 123 行使用）；`stack_trace_save_tsk` kernel/stacktrace.c:150（F3，第 152 行使用）；`stack_trace_save_tsk` kernel/stacktrace.c:150（F3，第 151 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、loongarch 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 37. 接口 `clock_getres_fallback`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/include/asm/vdso/gettimeofday.h:54 → effect；arm64 arch arch/arm64/include/asm/vdso/gettimeofday.h:58 → effect；x86_64 arch arch/x86/include/asm/vdso/gettimeofday.h:71 → effect
- 可疑调用位置：`__cvdso_clock_getres_data` lib/vdso/gettimeofday.c:421（F3，第 421 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 38. 接口 `clock_gettime_fallback`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/include/asm/vdso/gettimeofday.h:38 → effect；arm64 arch arch/arm64/include/asm/vdso/gettimeofday.h:41 → effect；x86_64 arch arch/x86/include/asm/vdso/gettimeofday.h:58 → effect
- 可疑调用位置：`__cvdso_clock_gettime_data` lib/vdso/gettimeofday.c:278（F3，第 278 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 39. 接口 `copy_thread`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/process.c:195 → effect（mem）；arm64 arch arch/arm64/kernel/process.c:413 → effect（mem）；x86_64 arch arch/x86/kernel/process.c:170 → effect（mem）
- 可疑调用位置：`copy_process` kernel/fork.c:2383（F3，第 2387 行使用）；`copy_process` kernel/fork.c:2383（F3，第 2390 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arc、arm 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 40. 接口 `futex_atomic_cmpxchg_inatomic`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/include/asm/futex.h:76 → effect（mem）；arm64 arch arch/arm64/include/asm/futex.h:285 → effect（mem）；x86_64 arch arch/x86/include/asm/futex.h:77 → effect（mem）
- 可疑调用位置：`futex_cmpxchg_value_locked` kernel/futex/core.c:458（F2，第 461 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arc、arm 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 41. 接口 `huge_ptep_modify_prot_commit`（未定性，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv generic include/linux/hugetlb.h:990 → effect（cache+mem+pgtable+tlb）；arm64 arch arch/arm64/mm/hugetlbpage.c:533 → effect（barrier+mem+pgtable+tlb）；x86_64 generic include/linux/hugetlb.h:1066 → effect（mem+pgtable）
- 可疑调用位置：`hugetlb_change_protection` mm/hugetlb.c:6975（F3，第 6995 行使用）；`hugetlb_change_protection` mm/hugetlb.c:6975（F3，第 6981 行使用）；`hugetlb_change_protection` mm/hugetlb.c:6975（F3，第 6981 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 42. 接口 `huge_ptep_set_wrprotect`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/mm/hugetlbpage.c:309 → effect（cache+mem+pgtable+tlb）；arm64 arch arch/arm64/mm/hugetlbpage.c:453 → effect（barrier+mem+pgtable+tlb）；x86_64 generic include/asm-generic/hugetlb.h:101 → effect:mem+pgtable（mem+pgtable）
- 可疑调用位置：`copy_hugetlb_page_range` mm/hugetlb.c:5503（F3，第 5518 行使用）；`copy_hugetlb_page_range` mm/hugetlb.c:5503（F3，第 5510 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、parisc、powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 43. 接口 `kprobe_fault_handler`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv generic include/linux/kprobes.h:453 → none；arm64 generic include/linux/kprobes.h:445 → none；x86_64 arch arch/x86/kernel/kprobes/core.c:1030 → effect（mem）
- 可疑调用位置：`kprobe_page_fault` include/linux/kprobes.h:600（F3，第 600 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arc、arm、arm64 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 44. 接口 `kvm_arch_flush_shadow_all`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kvm/mmu.c:417 → effect（mem+pgtable+tlb）；arm64 arch arch/arm64/kvm/nested.c:1318 → effect（mem）；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_flush_shadow_all` virt/kvm/kvm_main.c:384（F3，第 385 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 45. 接口 `kvm_arch_init_vm`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kvm/vm.c:30 → effect（mem+pgtable+tlb）；arm64 arch arch/arm64/kvm/arm.c:222 → effect（mem+register）；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_create_vm` virt/kvm/kvm_main.c:1219（F3，第 1228 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 46. 接口 `kvm_arch_prepare_memory_region`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kvm/mmu.c:447 → effect:mem+pgtable+tlb（mem+pgtable+tlb）；arm64 arch arch/arm64/kvm/mmu.c:2619 → effect:mem（mem）；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_prepare_memory_region` virt/kvm/kvm_main.c:1684（F3，第 1687 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 47. 接口 `kvm_arch_vcpu_create`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:105 → effect（mem）；arm64 arch arch/arm64/kvm/arm.c:537 → effect（barrier+mem+register）；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vm_ioctl_create_vcpu` virt/kvm/kvm_main.c:4258（F3，第 4263 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 48. 接口 `kvm_arch_vcpu_in_kernel`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:224 → effect；arm64 arch arch/arm64/kvm/arm.c:857 → effect；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_arch_vcpu_preempted_in_kernel` virt/kvm/kvm_main.c:4021（F3，第 4021 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 49. 接口 `kvm_arch_vcpu_ioctl`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:255 → effect（mem）；arm64 arch arch/arm64/kvm/arm.c:1855 → effect（barrier+cache+mem+tlb）；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4655（F2，第 4661 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 50. 接口 `kvm_arch_vcpu_ioctl_get_mpstate`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:485 → effect:mem（mem）；arm64 arch arch/arm64/kvm/arm.c:804 → effect:mem（mem）；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4547（F3，第 4562 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、s390 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

