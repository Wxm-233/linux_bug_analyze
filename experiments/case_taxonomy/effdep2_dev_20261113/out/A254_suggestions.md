# 人工分析建议（第二版）：A254

接口 8858 个；候选位置 20870 个，按接口聚合为 986 条；Q-多数 45、Q-类别 20、特性专有 92。以下为前 50 条。

## 1. 接口 `arch_dup_mmap`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、powerpc、x86）
- 各架构实现：riscv generic include/asm-generic/mm_hooks.h:10 → none；arm64 arch arch/arm64/include/asm/mmu_context.h:185 → effect:mem（mem）；x86_64 arch arch/x86/include/asm/mmu_context.h:218 → effect（mem+pgtable+tlb）
- 可疑调用位置：`dup_mmap` mm/mmap.c:1848（F3，第 1853 行使用）；`dup_mmap` mm/mmap.c:1848（F3，第 1853 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、powerpc、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 9.0

## 2. 接口 `kvm_arch_create_vm_debugfs`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、powerpc、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kvm/arm.c:295 → unknown；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_create_vm_debugfs` virt/kvm/kvm_main.c:1062（F3，第 1065 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、powerpc、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 9.0

## 3. 接口 `kvm_arch_vcpu_ioctl_set_sregs`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（powerpc、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:319 → none；arm64 arch arch/arm64/kvm/guest.c:742 → none；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4533（F3，第 4539 行使用）；`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4533（F3，第 4652 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 powerpc、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 9.0

## 4. 接口 `kvm_arch_vm_ioctl`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：riscv 没有实现或是空实现，而 6 个其他架构有实际实现（arm64、loongarch、mips、powerpc、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vm.c:268 → none；arm64 arch arch/arm64/kvm/arm.c:2034 → effect（barrier+mem）；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vm_ioctl` virt/kvm/kvm_main.c:5381（F2，第 5384 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 9.0

## 5. 接口 `__cpu_die`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 9 个其他架构有实际实现（loongarch、mips、parisc、powerpc、s390、sh、sparc、x86）
- 各架构实现：riscv arch arch/riscv/include/asm/smp.h:68 → none；arm64 arch arch/arm64/include/asm/smp.h:113 → none；x86_64 arch arch/x86/include/asm/smp.h:76 → unknown
- 可疑调用位置：`takedown_cpu` kernel/cpu.c:1341（F3，第 1343 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 loongarch、mips、parisc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 6. 接口 `arch_enter_from_user_mode`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（powerpc、s390、x86）
- 各架构实现：riscv generic include/linux/irq-entry-common.h:59 → none；arm64 generic include/linux/irq-entry-common.h:59 → none；x86_64 arch arch/x86/include/asm/entry-common.h:13 → unknown
- 可疑调用位置：`enter_from_user_mode` include/linux/irq-entry-common.h:100（F3，第 107 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 powerpc、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 7. 接口 `arch_override_mprotect_pkey`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、powerpc、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/include/asm/pkeys.h:27 → unknown；x86_64 arch arch/x86/include/asm/pkeys.h:34 → effect:mem（mem）
- 可疑调用位置：`do_mprotect_pkey` mm/mprotect.c:931（F3，第 933 行使用）；`do_mprotect_pkey` mm/mprotect.c:931（F3，第 932 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、powerpc、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 8. 接口 `arch_prctl_spec_ctrl_get`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、powerpc、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kernel/proton-pack.c:798 → unknown；x86_64 arch arch/x86/kernel/cpu/bugs.c:2735 → unknown
- 可疑调用位置：`__do_sys_prctl` kernel/sys.c:2747（F3，第 2752 行使用）；`__do_sys_prctl` kernel/sys.c:2747（F3，第 2752 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、powerpc、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 9. 接口 `arch_probe_nr_irqs`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm、loongarch、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 无实现  → unknown；x86_64 arch arch/x86/kernel/apic/vector.c:717 → effect
- 可疑调用位置：`early_irq_init` kernel/irq/irqdesc.c:560（F2，第 561 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、loongarch、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 10. 接口 `arch_vma_name`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（arm、hexagon、nios2、sh、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 无实现  → unknown；x86_64 无实现  → unknown
- 可疑调用位置：`perf_event_mmap_event` kernel/events/core.c:9811（F3，第 9813 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、hexagon、nios2 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 11. 接口 `flush_anon_page`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（arm、csky、mips、parisc、sh）
- 各架构实现：riscv generic include/linux/highmem.h:186 → none；arm64 generic include/linux/highmem.h:186 → none；x86_64 generic include/linux/highmem.h:186 → none
- 可疑调用位置：`__get_user_pages` mm/gup.c:1499（F3，第 1500 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、csky、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 12. 接口 `flush_cache_dup_mm`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 9 个其他架构有实际实现（arm、csky、m68k、mips、nios2、parisc、sh、sparc）
- 各架构实现：riscv generic include/asm-generic/cacheflush.h:29 → none；arm64 generic include/asm-generic/cacheflush.h:29 → none；x86_64 generic include/asm-generic/cacheflush.h:29 → none
- 可疑调用位置：`dup_mmap` mm/mmap.c:1741（F3，第 1742 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、csky、m68k 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 13. 接口 `flush_ptrace_hw_breakpoint`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 7 个其他架构有实际实现（arm、arm64、loongarch、powerpc、sh、x86、xtensa）
- 各架构实现：riscv generic include/linux/hw_breakpoint.h:137 → none；arm64 arch arch/arm64/kernel/ptrace.c:207 → effect:barrier+mem（barrier+mem）；x86_64 arch arch/x86/kernel/hw_breakpoint.c:470 → effect:barrier+mem（barrier+mem）
- 可疑调用位置：`do_exit` kernel/exit.c:1013（F3，第 1016 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、loongarch 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 14. 接口 `gup_fast_permitted`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（mips、s390、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 无实现  → unknown；x86_64 arch arch/x86/include/asm/pgtable_64.h:260 → unknown
- 可疑调用位置：`gup_fast` mm/gup.c:3137（F3，第 3157 行使用）；`gup_fast` mm/gup.c:3137（F3，第 3157 行使用）；`gup_fast` mm/gup.c:3137（F2，第 3137 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 mips、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 15. 接口 `kvm_arch_flush_remote_tlbs`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、mips、x86）
- 各架构实现：riscv generic include/linux/kvm_host.h:1696 → none；arm64 arch arch/arm64/kvm/mmu.c:175 → effect:barrier+mem+tlb（barrier+mem+tlb）；x86_64 generic include/linux/kvm_host.h:1723 → none
- 可疑调用位置：`kvm_flush_remote_tlbs` virt/kvm/kvm_main.c:308（F3，第 309 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、mips、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 16. 接口 `kvm_arch_intc_initialized`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、loongarch、powerpc）
- 各架构实现：riscv generic include/linux/kvm_host.h:1764 → none；arm64 arch arch/arm64/kvm/arm.c:1006 → unknown；x86_64 generic include/linux/kvm_host.h:1791 → none
- 可疑调用位置：`kvm_irqfd_assign` virt/kvm/eventfd.c:380（F3，第 383 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 17. 接口 `kvm_arch_para_features`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（loongarch、powerpc、x86）
- 各架构实现：riscv generic include/asm-generic/kvm_para.h:17 → none；arm64 generic include/asm-generic/kvm_para.h:17 → none；x86_64 arch arch/x86/kernel/kvm.c:916 → effect（mem）
- 可疑调用位置：`kvm_para_has_feature` include/linux/kvm_para.h:10（F2，第 10 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 loongarch、powerpc、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 18. 接口 `kvm_arch_vcpu_ioctl_get_fpu`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（loongarch、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:325 → none；arm64 arch arch/arm64/kvm/guest.c:855 → none；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4609（F3，第 4625 行使用）；`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4609（F3，第 4613 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 loongarch、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 19. 接口 `kvm_arch_vcpu_ioctl_get_regs`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（loongarch、mips、powerpc、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:341 → none；arm64 arch arch/arm64/kvm/guest.c:536 → none；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4489（F3，第 4508 行使用）；`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4489（F3，第 4493 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 loongarch、mips、powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 20. 接口 `kvm_arch_vcpu_ioctl_get_sregs`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（powerpc、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:313 → none；arm64 arch arch/arm64/kvm/guest.c:736 → none；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4517（F3，第 4533 行使用）；`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4517（F3，第 4521 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 powerpc、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 21. 接口 `kvm_arch_vcpu_ioctl_set_fpu`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（loongarch、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:330 → none；arm64 arch arch/arm64/kvm/guest.c:860 → none；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4625（F3，第 4629 行使用）；`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4625（F3，第 4651 行使用）；`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4625（F2，第 4653 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 loongarch、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 22. 接口 `kvm_arch_vcpu_ioctl_set_regs`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（loongarch、mips、powerpc、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:346 → none；arm64 arch arch/arm64/kvm/guest.c:541 → none；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4508（F3，第 4517 行使用）；`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4508（F3，第 4509 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 loongarch、mips、powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 23. 接口 `kvm_arch_vcpu_precreate`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:124 → none；arm64 arch arch/arm64/kvm/arm.c:526 → unknown；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vm_ioctl_create_vcpu` virt/kvm/kvm_main.c:4176（F3，第 4178 行使用）；`kvm_vm_ioctl_create_vcpu` virt/kvm/kvm_main.c:4176（F3，第 4199 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 24. 接口 `ptrace_disable`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 14 个其他架构有实际实现（alpha、arm64、csky、hexagon、loongarch、m68k、mips、openrisc）
- 各架构实现：riscv arch arch/riscv/kernel/ptrace.c:540 → none；arm64 arch arch/arm64/kernel/ptrace.c:157 → effect（mem）；x86_64 arch arch/x86/kernel/ptrace.c:718 → effect（mem）
- 可疑调用位置：`ptrace_detach` kernel/ptrace.c:595（F3，第 602 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 25. 接口 `user_disable_single_step`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 13 个其他架构有实际实现（alpha、arm64、csky、hexagon、loongarch、m68k、parisc、powerpc）
- 各架构实现：riscv generic include/linux/ptrace.h:302 → none；arm64 arch arch/arm64/kernel/debug-monitors.c:388 → effect（mem）；x86_64 arch arch/x86/kernel/step.c:229 → effect（mem）
- 可疑调用位置：`copy_process` kernel/fork.c:2355（F3，第 2356 行使用）；`ptrace_resume` kernel/ptrace.c:876（F3，第 888 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 5.6784

## 26. 接口 `arch_release_task_struct`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/kernel/process.c:209 → unknown；arm64 arch arch/arm64/kernel/process.c:344 → effect:mem（mem）；x86_64 arch arch/x86/kernel/process.c:118 → effect:mem（mem）
- 可疑调用位置：`free_task` kernel/fork.c:556（F3，第 557 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、s390、sh 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 27. 接口 `arch_tlbbatch_flush`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 barrier 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/mm/tlbflush.c:237 → effect（mem+tlb）；arm64 arch arch/arm64/include/asm/tlbflush.h:403 → effect:barrier+tlb（barrier+tlb）；x86_64 arch arch/x86/mm/tlb.c:1682 → effect（barrier+mem+tlb）
- 可疑调用位置：`try_to_unmap_flush` mm/rmap.c:718（F3，第 719 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 28. 接口 `set_direct_map_invalid_noflush`（Q-类别，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 的实现缺少 mem、pgtable 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/mm/pageattr.c:377 → effect:tlb（tlb）；arm64 arch arch/arm64/mm/pageattr.c:254 → effect:mem+pgtable（mem+pgtable）；x86_64 arch arch/x86/mm/pat/set_memory.c:2659 → effect:mem+pgtable（mem+pgtable）
- 可疑调用位置：`secretmem_fault` mm/secretmem.c:75（F3，第 77 行使用）；`secretmem_fault` mm/secretmem.c:75（F2，第 78 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、s390 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 29. 接口 `set_memory_x`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 barrier、mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/mm/pageattr.c:367 → effect（tlb）；arm64 arch arch/arm64/mm/pageattr.c:235 → effect（barrier+mem+tlb）；x86_64 arch arch/x86/mm/pat/set_memory.c:2317 → effect（barrier+cache+mem+pgtable+tlb）
- 可疑调用位置：`set_memory_rox` include/linux/set_memory.h:23（F3，第 23 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、loongarch 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 30. 接口 `tlb_flush`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 barrier 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/include/asm/tlb.h:16 → effect:tlb（tlb）；arm64 arch arch/arm64/include/asm/tlb.h:53 → effect:barrier+tlb（barrier+tlb）；x86_64 arch arch/x86/include/asm/tlb.h:13 → effect（barrier+mem+tlb）
- 可疑调用位置：`tlb_flush_mmu_tlbonly` include/asm-generic/tlb.h:509（F3，第 510 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 31. 接口 `user_enable_single_step`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv generic include/linux/ptrace.h:288 → unknown；arm64 arch arch/arm64/kernel/debug-monitors.c:379 → effect（mem）；x86_64 arch arch/x86/kernel/step.c:219 → effect（mem）
- 可疑调用位置：`ptrace_resume` kernel/ptrace.c:874（F3，第 876 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 32. 接口 `wrprotect_ptes`（Q-类别，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 pgtable 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv generic include/linux/pgtable.h:1134 → effect:mem（mem）；arm64 arch arch/arm64/include/asm/pgtable.h:1902 → effect:mem+pgtable+tlb（mem+pgtable+tlb）；x86_64 generic include/linux/pgtable.h:1115 → effect:mem+pgtable（mem+pgtable）
- 可疑调用位置：`__copy_present_ptes` mm/memory.c:1106（F3，第 1118 行使用）；`__copy_present_ptes` mm/memory.c:1106（F3，第 1118 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 33. 接口 `destroy_context`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 11 个其他架构有实际实现（arc、m68k、microblaze、mips、openrisc、parisc、powerpc、sparc）
- 各架构实现：riscv generic include/asm-generic/mmu_context.h:46 → none；arm64 generic include/asm-generic/mmu_context.h:46 → none；x86_64 arch arch/x86/include/asm/mmu_context.h:172 → effect（mem）
- 可疑调用位置：`__mmdrop` kernel/fork.c:735（F3，第 736 行使用）；`mm_init` kernel/fork.c:1148（F3，第 1150 行使用）；`mm_init` kernel/fork.c:1148（F2，第 1148 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arc、m68k、microblaze 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.7856

## 34. 接口 `exit_thread`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（arm、mips、sparc、x86、xtensa）
- 各架构实现：riscv generic include/linux/sched/task.h:89 → none；arm64 generic include/linux/sched/task.h:90 → none；x86_64 arch arch/x86/kernel/process.c:128 → effect（mem）
- 可疑调用位置：`do_exit` kernel/exit.c:1005（F3，第 1007 行使用）；`copy_process` kernel/fork.c:2576（F3，第 2578 行使用）；`copy_process` kernel/fork.c:2576（F2，第 2576 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、mips、sparc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.7856

## 35. 接口 `flush_cache_mm`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 8 个其他架构有实际实现（arm、csky、m68k、nios2、parisc、sh、sparc、xtensa）
- 各架构实现：riscv generic include/asm-generic/cacheflush.h:23 → none；arm64 generic include/asm-generic/cacheflush.h:23 → none；x86_64 generic include/asm-generic/cacheflush.h:23 → none
- 可疑调用位置：`exit_mmap` mm/mmap.c:1296（F3，第 1297 行使用）；`dup_mmap` mm/mmap.c:1890（F3，第 1892 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、csky、m68k 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.7856

## 36. 接口 `flush_icache_pages`（Q-多数，5 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（alpha、m68k、nios2、parisc、sh）
- 各架构实现：riscv generic include/linux/cacheflush.h:21 → none；arm64 generic include/linux/cacheflush.h:21 → none；x86_64 generic include/linux/cacheflush.h:21 → none
- 可疑调用位置：`do_swap_page` mm/memory.c:5063（F3，第 5068 行使用）；`do_swap_page` mm/memory.c:5063（F3，第 5082 行使用）；`do_swap_page` mm/memory.c:5063（F3，第 5082 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、m68k、nios2 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.7856

## 37. 接口 `flush_kernel_vmap_range`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（arm、csky、mips、parisc、sh）
- 各架构实现：riscv generic include/linux/highmem.h:192 → none；arm64 generic include/linux/highmem.h:192 → none；x86_64 generic include/linux/highmem.h:192 → none
- 可疑调用位置：`ring_buffer_map_get_reader` kernel/trace/ring_buffer.c:7925（F3，第 7928 行使用）；`ring_buffer_map_get_reader` kernel/trace/ring_buffer.c:7925（F3，第 7926 行使用）；`ring_buffer_map_get_reader` kernel/trace/ring_buffer.c:7925（F2，第 7925 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、csky、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.7856

## 38. 接口 `module_arch_cleanup`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 7 个其他架构有实际实现（arc、arm、mips、parisc、s390、sh、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 无实现  → unknown；x86_64 arch arch/x86/kernel/module.c:309 → effect:mem（mem）
- 可疑调用位置：`free_module` kernel/module/main.c:1434（F3，第 1437 行使用）；`load_module` kernel/module/main.c:3602（F3，第 3604 行使用）；`load_module` kernel/module/main.c:3602（F2，第 3602 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arc、arm、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.7856

## 39. 接口 `__arch_get_hw_counter`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/include/asm/vdso/gettimeofday.h:63 → unknown；arm64 arch arch/arm64/include/asm/vdso/gettimeofday.h:74 → unknown；x86_64 arch arch/x86/include/asm/vdso/gettimeofday.h:146 → unknown
- 可疑调用位置：`vdso_get_timestamp` lib/vdso/gettimeofday.c:118（F3，第 122 行使用）；`vdso_get_timestamp` lib/vdso/gettimeofday.c:118（F2，第 119 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、loongarch 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 40. 接口 `__get_wchan`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/stacktrace.c:168 → effect（mem）；arm64 arch arch/arm64/kernel/process.c:796 → effect（mem）；x86_64 arch arch/x86/kernel/process.c:1041 → effect（mem）
- 可疑调用位置：`get_wchan` kernel/sched/core.c:2166（F3，第 2167 行使用）；`get_wchan` kernel/sched/core.c:2166（F2，第 2169 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arc、arm 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 41. 接口 `arch_bpf_stack_walk`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 4 个其他架构有实际实现（arm64、powerpc、s390、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kernel/stacktrace.c:437 → effect:mem（mem）；x86_64 无实现  → unknown
- 可疑调用位置：`bpf_prog_find_from_stack` kernel/bpf/core.c:3533（F3，第 3534 行使用）；`bpf_throw` kernel/bpf/helpers.c:3392（F3，第 3393 行使用）；`bpf_stream_stage_dump_stack` kernel/bpf/stream.c:398（F3，第 399 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、powerpc、s390 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 42. 接口 `arch_dup_task_struct`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/process.c:216 → effect（mem）；arm64 arch arch/arm64/kernel/process.c:349 → effect（mem）；x86_64 arch arch/x86/kernel/process.c:105 → effect（mem）
- 可疑调用位置：`dup_task_struct` kernel/fork.c:925（F3，第 929 行使用）；`dup_task_struct` kernel/fork.c:925（F3，第 963 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 43. 接口 `arch_set_shadow_stack_status`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/mm/gcs.c:159 → effect（mem）；x86_64 无实现  → unknown
- 可疑调用位置：`__do_sys_prctl` kernel/sys.c:2872（F3，第 2877 行使用）；`__do_sys_prctl` kernel/sys.c:2872（F3，第 2877 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 44. 接口 `arch_stack_walk`（Q-类别，4 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/kernel/stacktrace.c:179 → unknown；arm64 arch arch/arm64/kernel/stacktrace.c:381 → effect:mem（mem）；x86_64 arch arch/x86/kernel/stacktrace.c:15 → effect:mem（mem）
- 可疑调用位置：`stack_trace_save` kernel/stacktrace.c:122（F3，第 123 行使用）；`stack_trace_save_tsk` kernel/stacktrace.c:150（F3，第 152 行使用）；`stack_trace_save_tsk` kernel/stacktrace.c:150（F3，第 151 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、loongarch 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 45. 接口 `arch_thread_struct_whitelist`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/include/asm/processor.h:129 → effect（mem）；arm64 arch arch/arm64/include/asm/processor.h:269 → effect（mem）；x86_64 arch arch/x86/include/asm/processor.h:545 → effect（mem）
- 可疑调用位置：`task_struct_whitelist` kernel/fork.c:842（F3，第 849 行使用）；`task_struct_whitelist` kernel/fork.c:842（F3，第 848 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 46. 接口 `arch_uprobe_analyze_insn`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/probes/uprobes.c:31 → effect（mem）；arm64 无实现  → unknown；x86_64 arch arch/x86/kernel/uprobes.c:1626 → effect（mem）
- 可疑调用位置：`prepare_uprobe` kernel/events/uprobes.c:1117（F3，第 1122 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 47. 接口 `arch_uprobe_skip_sstep`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/probes/uprobes.c:91 → unknown；arm64 无实现  → unknown；x86_64 arch arch/x86/kernel/uprobes.c:1842 → unknown
- 可疑调用位置：`handle_swbp` kernel/events/uprobes.c:2782（F3，第 2785 行使用）；`handle_swbp` kernel/events/uprobes.c:2782（F3，第 2785 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 48. 接口 `arch_uretprobe_hijack_return_addr`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/probes/uprobes.c:130 → effect（mem）；arm64 无实现  → unknown；x86_64 arch arch/x86/kernel/uprobes.c:1851 → effect:mem（mem）
- 可疑调用位置：`prepare_uretprobe` kernel/events/uprobes.c:2271（F3，第 2277 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 49. 接口 `clear_user_highpage`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv generic include/linux/highmem.h:262 → effect（mem）；arm64 generic include/linux/highmem.h:262 → effect（mem）；x86_64 generic include/linux/highmem.h:262 → effect（mem）
- 可疑调用位置：`vma_alloc_zeroed_movable_folio` include/linux/highmem.h:327（F3，第 329 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、sh、xtensa 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 50. 接口 `clock_getres_fallback`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/include/asm/vdso/gettimeofday.h:48 → effect；arm64 arch arch/arm64/include/asm/vdso/gettimeofday.h:58 → effect；x86_64 arch arch/x86/include/asm/vdso/gettimeofday.h:71 → effect
- 可疑调用位置：`__cvdso_clock_getres_data` lib/vdso/gettimeofday.c:456（F3，第 456 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、loongarch 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

