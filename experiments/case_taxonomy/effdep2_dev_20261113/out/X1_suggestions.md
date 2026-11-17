# 人工分析建议（第二版）：X1

接口 9016 个；候选位置 20126 个，按接口聚合为 978 条；Q-多数 46、Q-类别 26、特性专有 99。以下为前 50 条。

## 1. 接口 `arch_dup_mmap`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、powerpc、x86）
- 各架构实现：riscv generic include/asm-generic/mm_hooks.h:10 → none；arm64 arch arch/arm64/include/asm/mmu_context.h:185 → effect:mem（mem）；x86_64 arch arch/x86/include/asm/mmu_context.h:218 → effect（mem+pgtable+tlb）
- 可疑调用位置：`dup_mmap` mm/mmap.c:1842（F3，第 1847 行使用）；`dup_mmap` mm/mmap.c:1842（F3，第 1847 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、powerpc、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 9.0

## 2. 接口 `kvm_arch_create_vm_debugfs`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、powerpc、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kvm/arm.c:295 → unknown；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_create_vm_debugfs` virt/kvm/kvm_main.c:1081（F3，第 1084 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、powerpc、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 9.0

## 3. 接口 `kvm_arch_vcpu_ioctl_set_sregs`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（powerpc、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:315 → none；arm64 arch arch/arm64/kvm/guest.c:742 → none；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4533（F3，第 4539 行使用）；`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4533（F3，第 4652 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 powerpc、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 9.0

## 4. 接口 `kvm_arch_vm_ioctl`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：riscv 没有实现或是空实现，而 6 个其他架构有实际实现（arm64、loongarch、mips、powerpc、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vm.c:226 → none；arm64 arch arch/arm64/kvm/arm.c:2034 → effect（barrier+mem）；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vm_ioctl` virt/kvm/kvm_main.c:5380（F2，第 5383 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 9.0

## 5. 接口 `__cpu_die`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 9 个其他架构有实际实现（loongarch、mips、parisc、powerpc、s390、sh、sparc、x86）
- 各架构实现：riscv arch arch/riscv/include/asm/smp.h:68 → none；arm64 arch arch/arm64/include/asm/smp.h:113 → none；x86_64 arch arch/x86/include/asm/smp.h:76 → unknown
- 可疑调用位置：`takedown_cpu` kernel/cpu.c:1337（F3，第 1339 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 loongarch、mips、parisc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 6. 接口 `arch_override_mprotect_pkey`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、powerpc、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/include/asm/pkeys.h:27 → unknown；x86_64 arch arch/x86/include/asm/pkeys.h:34 → effect:mem（mem）
- 可疑调用位置：`do_mprotect_pkey` mm/mprotect.c:955（F3，第 957 行使用）；`do_mprotect_pkey` mm/mprotect.c:955（F3，第 956 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、powerpc、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 7. 接口 `arch_prctl_spec_ctrl_get`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、powerpc、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kernel/proton-pack.c:798 → unknown；x86_64 arch arch/x86/kernel/cpu/bugs.c:2735 → unknown
- 可疑调用位置：`__do_sys_prctl` kernel/sys.c:2731（F3，第 2736 行使用）；`__do_sys_prctl` kernel/sys.c:2731（F3，第 2736 行使用）；`__do_sys_prctl` kernel/sys.c:2731（F2，第 2876 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、powerpc、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 8. 接口 `arch_probe_nr_irqs`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm、loongarch、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 无实现  → unknown；x86_64 arch arch/x86/kernel/apic/vector.c:717 → effect
- 可疑调用位置：`early_irq_init` kernel/irq/irqdesc.c:557（F2，第 558 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、loongarch、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 9. 接口 `arch_vma_name`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（arm、hexagon、nios2、sh、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 无实现  → unknown；x86_64 无实现  → unknown
- 可疑调用位置：`perf_event_mmap_event` kernel/events/core.c:9436（F3，第 9438 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、hexagon、nios2 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 10. 接口 `flush_anon_page`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（arm、csky、mips、parisc、sh）
- 各架构实现：riscv generic include/linux/highmem.h:186 → none；arm64 generic include/linux/highmem.h:186 → none；x86_64 generic include/linux/highmem.h:186 → none
- 可疑调用位置：`__get_user_pages` mm/gup.c:1499（F3，第 1500 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、csky、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 11. 接口 `flush_cache_dup_mm`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 9 个其他架构有实际实现（arm、csky、m68k、mips、nios2、parisc、sh、sparc）
- 各架构实现：riscv generic include/asm-generic/cacheflush.h:29 → none；arm64 generic include/asm-generic/cacheflush.h:29 → none；x86_64 generic include/asm-generic/cacheflush.h:29 → none
- 可疑调用位置：`dup_mmap` mm/mmap.c:1729（F3，第 1730 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、csky、m68k 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 12. 接口 `flush_cache_mm`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 8 个其他架构有实际实现（arm、csky、m68k、nios2、parisc、sh、sparc、xtensa）
- 各架构实现：riscv generic include/asm-generic/cacheflush.h:23 → none；arm64 generic include/asm-generic/cacheflush.h:23 → none；x86_64 generic include/asm-generic/cacheflush.h:23 → none
- 可疑调用位置：`exit_mmap` mm/mmap.c:1276（F3，第 1277 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、csky、m68k 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 13. 接口 `flush_ptrace_hw_breakpoint`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 7 个其他架构有实际实现（arm、arm64、loongarch、powerpc、sh、x86、xtensa）
- 各架构实现：riscv generic include/linux/hw_breakpoint.h:137 → none；arm64 arch arch/arm64/kernel/ptrace.c:207 → effect:barrier+mem（barrier+mem）；x86_64 arch arch/x86/kernel/hw_breakpoint.c:470 → effect:barrier+mem（barrier+mem）
- 可疑调用位置：`do_exit` kernel/exit.c:975（F3，第 978 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、loongarch 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 14. 接口 `gup_fast_permitted`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（mips、s390、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 无实现  → unknown；x86_64 arch arch/x86/include/asm/pgtable_64.h:260 → unknown
- 可疑调用位置：`gup_fast` mm/gup.c:3148（F3，第 3168 行使用）；`gup_fast` mm/gup.c:3148（F3，第 3168 行使用）；`gup_fast` mm/gup.c:3148（F2，第 3148 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 mips、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 15. 接口 `kvm_arch_flush_remote_tlbs`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、mips、x86）
- 各架构实现：riscv generic include/linux/kvm_host.h:1673 → none；arm64 arch arch/arm64/kvm/mmu.c:175 → effect:barrier+mem+tlb（barrier+mem+tlb）；x86_64 generic include/linux/kvm_host.h:1723 → none
- 可疑调用位置：`kvm_flush_remote_tlbs` virt/kvm/kvm_main.c:308（F3，第 309 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、mips、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 16. 接口 `kvm_arch_intc_initialized`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、loongarch、powerpc）
- 各架构实现：riscv generic include/linux/kvm_host.h:1741 → none；arm64 arch arch/arm64/kvm/arm.c:1006 → unknown；x86_64 generic include/linux/kvm_host.h:1791 → none
- 可疑调用位置：`kvm_irqfd_assign` virt/kvm/eventfd.c:365（F3，第 368 行使用）
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
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:321 → none；arm64 arch arch/arm64/kvm/guest.c:855 → none；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4609（F3，第 4625 行使用）；`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4609（F3，第 4613 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 loongarch、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 19. 接口 `kvm_arch_vcpu_ioctl_get_regs`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（loongarch、mips、powerpc、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:337 → none；arm64 arch arch/arm64/kvm/guest.c:536 → none；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4489（F3，第 4508 行使用）；`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4489（F3，第 4493 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 loongarch、mips、powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 20. 接口 `kvm_arch_vcpu_ioctl_get_sregs`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（powerpc、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:309 → none；arm64 arch arch/arm64/kvm/guest.c:736 → none；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4517（F3，第 4533 行使用）；`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4517（F3，第 4521 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 powerpc、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 21. 接口 `kvm_arch_vcpu_ioctl_set_fpu`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（loongarch、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:326 → none；arm64 arch arch/arm64/kvm/guest.c:860 → none；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4625（F3，第 4629 行使用）；`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4625（F3，第 4651 行使用）；`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4625（F2，第 4653 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 loongarch、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 22. 接口 `kvm_arch_vcpu_ioctl_set_regs`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（loongarch、mips、powerpc、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:342 → none；arm64 arch arch/arm64/kvm/guest.c:541 → none；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4508（F3，第 4517 行使用）；`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4508（F3，第 4509 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 loongarch、mips、powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 23. 接口 `kvm_arch_vcpu_precreate`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:122 → none；arm64 arch arch/arm64/kvm/arm.c:526 → unknown；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vm_ioctl_create_vcpu` virt/kvm/kvm_main.c:4182（F3，第 4184 行使用）；`kvm_vm_ioctl_create_vcpu` virt/kvm/kvm_main.c:4182（F3，第 4205 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 24. 接口 `ptrace_disable`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 14 个其他架构有实际实现（alpha、arm64、csky、hexagon、loongarch、m68k、mips、openrisc）
- 各架构实现：riscv arch arch/riscv/kernel/ptrace.c:335 → none；arm64 arch arch/arm64/kernel/ptrace.c:157 → effect（mem）；x86_64 arch arch/x86/kernel/ptrace.c:718 → effect（mem）
- 可疑调用位置：`ptrace_detach` kernel/ptrace.c:569（F3，第 576 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 25. 接口 `user_disable_single_step`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 13 个其他架构有实际实现（alpha、arm64、csky、hexagon、loongarch、m68k、parisc、powerpc）
- 各架构实现：riscv generic include/linux/ptrace.h:301 → none；arm64 arch arch/arm64/kernel/debug-monitors.c:388 → effect（mem）；x86_64 arch arch/x86/kernel/step.c:229 → effect（mem）
- 可疑调用位置：`copy_process` kernel/fork.c:2242（F3，第 2243 行使用）；`ptrace_resume` kernel/ptrace.c:850（F3，第 862 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 5.6784

## 26. 接口 `arch_release_task_struct`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/kernel/process.c:193 → unknown；arm64 arch arch/arm64/kernel/process.c:344 → effect:mem（mem）；x86_64 arch arch/x86/kernel/process.c:118 → effect:mem（mem）
- 可疑调用位置：`free_task` kernel/fork.c:508（F3，第 509 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、s390、sh 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 27. 接口 `arch_tlbbatch_flush`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 barrier 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/mm/tlbflush.c:237 → effect（mem+tlb）；arm64 arch arch/arm64/include/asm/tlbflush.h:403 → effect:barrier+tlb（barrier+tlb）；x86_64 arch arch/x86/mm/tlb.c:1682 → effect（barrier+mem+tlb）
- 可疑调用位置：`try_to_unmap_flush` mm/rmap.c:649（F3，第 650 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 28. 接口 `p4d_free`（Q-类别，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv generic include/asm-generic/pgalloc.h:257 → unknown；arm64 generic include/asm-generic/pgalloc.h:268 → effect:mem（mem）；x86_64 generic include/asm-generic/pgalloc.h:268 → effect:mem（mem）
- 可疑调用位置：`__p4d_alloc` mm/memory.c:6550（F3，第 6553 行使用）；`__p4d_alloc` mm/memory.c:6550（F3，第 6553 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 s390 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 29. 接口 `pud_free`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/include/asm/pgalloc.h:83 → unknown；arm64 arch arch/arm64/include/asm/pgalloc.h:59 → effect:mem（mem）；x86_64 generic include/asm-generic/pgalloc.h:220 → effect:mem（mem）
- 可疑调用位置：`__pud_alloc` mm/memory.c:6577（F3，第 6578 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、powerpc、s390 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 30. 接口 `set_direct_map_invalid_noflush`（Q-类别，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 的实现缺少 mem、pgtable 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/mm/pageattr.c:377 → effect:tlb（tlb）；arm64 arch arch/arm64/mm/pageattr.c:254 → effect:mem+pgtable（mem+pgtable）；x86_64 arch arch/x86/mm/pat/set_memory.c:2659 → effect:mem+pgtable（mem+pgtable）
- 可疑调用位置：`secretmem_fault` mm/secretmem.c:75（F3，第 77 行使用）；`secretmem_fault` mm/secretmem.c:75（F2，第 78 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、s390 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 31. 接口 `set_memory_x`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 barrier、mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/mm/pageattr.c:367 → effect（tlb）；arm64 arch arch/arm64/mm/pageattr.c:235 → effect（barrier+mem+tlb）；x86_64 arch arch/x86/mm/pat/set_memory.c:2317 → effect（barrier+cache+mem+pgtable+tlb）
- 可疑调用位置：`set_memory_rox` include/linux/set_memory.h:23（F3，第 23 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、loongarch 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 32. 接口 `tlb_flush`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 barrier 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/include/asm/tlb.h:16 → effect:tlb（tlb）；arm64 arch arch/arm64/include/asm/tlb.h:53 → effect:barrier+tlb（barrier+tlb）；x86_64 arch arch/x86/include/asm/tlb.h:13 → effect（barrier+mem+tlb）
- 可疑调用位置：`tlb_flush_mmu_tlbonly` include/asm-generic/tlb.h:490（F3，第 491 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 33. 接口 `user_enable_single_step`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv generic include/linux/ptrace.h:287 → unknown；arm64 arch arch/arm64/kernel/debug-monitors.c:379 → effect（mem）；x86_64 arch arch/x86/kernel/step.c:219 → effect（mem）
- 可疑调用位置：`ptrace_resume` kernel/ptrace.c:848（F3，第 850 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 34. 接口 `wrprotect_ptes`（Q-类别，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem、pgtable 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv generic include/linux/pgtable.h:937 → unknown；arm64 arch arch/arm64/include/asm/pgtable.h:1902 → effect:mem+pgtable+tlb（mem+pgtable+tlb）；x86_64 generic include/linux/pgtable.h:1115 → effect:mem+pgtable（mem+pgtable）
- 可疑调用位置：`__copy_present_ptes` mm/memory.c:1089（F3，第 1101 行使用）；`__copy_present_ptes` mm/memory.c:1089（F3，第 1101 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 35. 接口 `destroy_context`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 11 个其他架构有实际实现（arc、m68k、microblaze、mips、openrisc、parisc、powerpc、sparc）
- 各架构实现：riscv generic include/asm-generic/mmu_context.h:46 → none；arm64 generic include/asm-generic/mmu_context.h:46 → none；x86_64 arch arch/x86/include/asm/mmu_context.h:172 → effect（mem）
- 可疑调用位置：`__mmdrop` kernel/fork.c:685（F3，第 686 行使用）；`mm_init` kernel/fork.c:1097（F3，第 1099 行使用）；`mm_init` kernel/fork.c:1097（F2，第 1097 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arc、m68k、microblaze 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.7856

## 36. 接口 `exit_thread`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（arm、mips、sparc、x86、xtensa）
- 各架构实现：riscv generic include/linux/sched/task.h:89 → none；arm64 generic include/linux/sched/task.h:90 → none；x86_64 arch arch/x86/kernel/process.c:128 → effect（mem）
- 可疑调用位置：`do_exit` kernel/exit.c:967（F3，第 969 行使用）；`copy_process` kernel/fork.c:2451（F3，第 2453 行使用）；`copy_process` kernel/fork.c:2451（F2，第 2451 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、mips、sparc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.7856

## 37. 接口 `flush_icache_pages`（Q-多数，5 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（alpha、m68k、nios2、parisc、sh）
- 各架构实现：riscv generic include/linux/cacheflush.h:21 → none；arm64 generic include/linux/cacheflush.h:21 → none；x86_64 generic include/linux/cacheflush.h:21 → none
- 可疑调用位置：`do_swap_page` mm/memory.c:4947（F3，第 4952 行使用）；`do_swap_page` mm/memory.c:4947（F3，第 4965 行使用）；`do_swap_page` mm/memory.c:4947（F3，第 4965 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、m68k、nios2 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.7856

## 38. 接口 `flush_kernel_vmap_range`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（arm、csky、mips、parisc、sh）
- 各架构实现：riscv generic include/linux/highmem.h:192 → none；arm64 generic include/linux/highmem.h:192 → none；x86_64 generic include/linux/highmem.h:192 → none
- 可疑调用位置：`ring_buffer_map_get_reader` kernel/trace/ring_buffer.c:7405（F3，第 7408 行使用）；`ring_buffer_map_get_reader` kernel/trace/ring_buffer.c:7405（F3，第 7406 行使用）；`ring_buffer_map_get_reader` kernel/trace/ring_buffer.c:7405（F2，第 7405 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、csky、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.7856

## 39. 接口 `module_arch_cleanup`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 7 个其他架构有实际实现（arc、arm、mips、parisc、s390、sh、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 无实现  → unknown；x86_64 arch arch/x86/kernel/module.c:309 → effect:mem（mem）
- 可疑调用位置：`free_module` kernel/module/main.c:1405（F3，第 1408 行使用）；`load_module` kernel/module/main.c:3531（F3，第 3533 行使用）；`load_module` kernel/module/main.c:3531（F2，第 3531 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arc、arm、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.7856

## 40. 接口 `__arch_get_hw_counter`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/include/asm/vdso/gettimeofday.h:71 → unknown；arm64 arch arch/arm64/include/asm/vdso/gettimeofday.h:74 → unknown；x86_64 arch arch/x86/include/asm/vdso/gettimeofday.h:146 → unknown
- 可疑调用位置：`vdso_get_timestamp` lib/vdso/gettimeofday.c:101（F3，第 105 行使用）；`vdso_get_timestamp` lib/vdso/gettimeofday.c:101（F2，第 102 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、loongarch 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 41. 接口 `__cpu_up`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/smpboot.c:182 → effect:mem（mem）；arm64 arch arch/arm64/kernel/smp.c:113 → effect:barrier+mem（barrier+mem）；x86_64 无实现  → unknown
- 可疑调用位置：`bringup_cpu` kernel/cpu.c:879（F3，第 883 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arc、arm 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 42. 接口 `__get_wchan`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/stacktrace.c:168 → effect（mem）；arm64 arch arch/arm64/kernel/process.c:796 → effect（mem）；x86_64 arch arch/x86/kernel/process.c:1041 → effect（mem）
- 可疑调用位置：`get_wchan` kernel/sched/core.c:2074（F3，第 2075 行使用）；`get_wchan` kernel/sched/core.c:2074（F2，第 2077 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arc、arm 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 43. 接口 `arch_bpf_stack_walk`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、s390、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kernel/stacktrace.c:437 → effect:mem（mem）；x86_64 无实现  → unknown
- 可疑调用位置：`bpf_prog_find_from_stack` kernel/bpf/core.c:3314（F3，第 3315 行使用）；`bpf_throw` kernel/bpf/helpers.c:3025（F3，第 3026 行使用）；`bpf_stream_stage_dump_stack` kernel/bpf/stream.c:523（F3，第 524 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 44. 接口 `arch_dup_task_struct`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/process.c:200 → effect（mem）；arm64 arch arch/arm64/kernel/process.c:349 → effect（mem）；x86_64 arch arch/x86/kernel/process.c:105 → effect（mem）
- 可疑调用位置：`dup_task_struct` kernel/fork.c:877（F3，第 881 行使用）；`dup_task_struct` kernel/fork.c:877（F3，第 913 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 45. 接口 `arch_stack_walk`（Q-类别，4 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/kernel/stacktrace.c:179 → unknown；arm64 arch arch/arm64/kernel/stacktrace.c:381 → effect:mem（mem）；x86_64 arch arch/x86/kernel/stacktrace.c:15 → effect:mem（mem）
- 可疑调用位置：`stack_trace_save` kernel/stacktrace.c:122（F3，第 123 行使用）；`stack_trace_save_tsk` kernel/stacktrace.c:150（F3，第 152 行使用）；`stack_trace_save_tsk` kernel/stacktrace.c:150（F3，第 151 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、loongarch 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 46. 接口 `arch_thread_struct_whitelist`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/include/asm/processor.h:128 → effect（mem）；arm64 arch arch/arm64/include/asm/processor.h:269 → effect（mem）；x86_64 arch arch/x86/include/asm/processor.h:545 → effect（mem）
- 可疑调用位置：`task_struct_whitelist` kernel/fork.c:794（F3，第 801 行使用）；`task_struct_whitelist` kernel/fork.c:794（F3，第 800 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 47. 接口 `arch_uprobe_analyze_insn`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/probes/uprobes.c:31 → effect（mem）；arm64 无实现  → unknown；x86_64 arch arch/x86/kernel/uprobes.c:1626 → effect（mem）
- 可疑调用位置：`prepare_uprobe` kernel/events/uprobes.c:1117（F3，第 1122 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 48. 接口 `arch_uprobe_skip_sstep`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/probes/uprobes.c:91 → unknown；arm64 无实现  → unknown；x86_64 arch arch/x86/kernel/uprobes.c:1842 → unknown
- 可疑调用位置：`handle_swbp` kernel/events/uprobes.c:2778（F3，第 2781 行使用）；`handle_swbp` kernel/events/uprobes.c:2778（F3，第 2781 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 49. 接口 `arch_uretprobe_hijack_return_addr`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/probes/uprobes.c:130 → effect（mem）；arm64 无实现  → unknown；x86_64 arch arch/x86/kernel/uprobes.c:1851 → effect:mem（mem）
- 可疑调用位置：`prepare_uretprobe` kernel/events/uprobes.c:2267（F3，第 2273 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 50. 接口 `clock_getres_fallback`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/include/asm/vdso/gettimeofday.h:54 → effect；arm64 arch arch/arm64/include/asm/vdso/gettimeofday.h:58 → effect；x86_64 arch arch/x86/include/asm/vdso/gettimeofday.h:71 → effect
- 可疑调用位置：`__cvdso_clock_getres_data` lib/vdso/gettimeofday.c:476（F3，第 476 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、loongarch 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

