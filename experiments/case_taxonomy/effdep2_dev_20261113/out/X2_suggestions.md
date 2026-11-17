# 人工分析建议（第二版）：X2

接口 8351 个；候选位置 18850 个，按接口聚合为 910 条；Q-多数 45、Q-类别 24、特性专有 103。以下为前 50 条。

## 1. 接口 `kvm_arch_create_vm_debugfs`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、powerpc、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kvm/arm.c:295 → unknown；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_create_vm_debugfs` virt/kvm/kvm_main.c:1110（F3，第 1113 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、powerpc、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 9.0

## 2. 接口 `kvm_arch_vcpu_ioctl_set_sregs`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（powerpc、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:304 → none；arm64 arch arch/arm64/kvm/guest.c:742 → none；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4479（F3，第 4485 行使用）；`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4479（F3，第 4584 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 powerpc、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 9.0

## 3. 接口 `kvm_arch_vm_ioctl`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（arm64、mips、powerpc、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vm.c:212 → none；arm64 arch arch/arm64/kvm/arm.c:2034 → effect（barrier+mem）；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vm_ioctl` virt/kvm/kvm_main.c:5309（F2，第 5312 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、mips、powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 9.0

## 4. 接口 `kvm_vm_ioctl_enable_cap`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 4 个其他架构有实际实现（arm64、powerpc、s390、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kvm/arm.c:135 → effect（mem）；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vm_ioctl_enable_cap_generic` virt/kvm/kvm_main.c:5015（F3，第 5015 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、powerpc、s390 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 9.0

## 5. 接口 `__cpu_die`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 9 个其他架构有实际实现（loongarch、mips、parisc、powerpc、s390、sh、sparc、x86）
- 各架构实现：riscv arch arch/riscv/include/asm/smp.h:68 → none；arm64 arch arch/arm64/include/asm/smp.h:113 → none；x86_64 arch arch/x86/include/asm/smp.h:76 → unknown
- 可疑调用位置：`takedown_cpu` kernel/cpu.c:1327（F3，第 1329 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 loongarch、mips、parisc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 6. 接口 `arch_prctl_spec_ctrl_get`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、powerpc、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kernel/proton-pack.c:798 → unknown；x86_64 arch arch/x86/kernel/cpu/bugs.c:2735 → unknown
- 可疑调用位置：`__do_sys_prctl` kernel/sys.c:2668（F3，第 2673 行使用）；`__do_sys_prctl` kernel/sys.c:2668（F3，第 2673 行使用）；`__do_sys_prctl` kernel/sys.c:2668（F2，第 2789 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、powerpc、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 7. 接口 `arch_vma_name`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 6 个其他架构有实际实现（arm、csky、hexagon、nios2、sh、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 无实现  → unknown；x86_64 无实现  → unknown
- 可疑调用位置：`perf_event_mmap_event` kernel/events/core.c:8789（F3，第 8791 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、csky、hexagon 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 8. 接口 `flush_anon_page`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（arm、csky、mips、parisc、sh）
- 各架构实现：riscv generic include/linux/highmem.h:186 → none；arm64 generic include/linux/highmem.h:186 → none；x86_64 generic include/linux/highmem.h:186 → none
- 可疑调用位置：`__get_user_pages` mm/gup.c:1662（F3，第 1663 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、csky、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 9. 接口 `flush_cache_dup_mm`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 9 个其他架构有实际实现（arm、csky、m68k、mips、nios2、parisc、sh、sparc）
- 各架构实现：riscv generic include/asm-generic/cacheflush.h:29 → none；arm64 generic include/asm-generic/cacheflush.h:29 → none；x86_64 generic include/asm-generic/cacheflush.h:29 → none
- 可疑调用位置：`dup_mmap` kernel/fork.c:642（F3，第 643 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、csky、m68k 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 10. 接口 `flush_cache_mm`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 8 个其他架构有实际实现（arm、csky、m68k、nios2、parisc、sh、sparc、xtensa）
- 各架构实现：riscv generic include/asm-generic/cacheflush.h:23 → none；arm64 generic include/asm-generic/cacheflush.h:23 → none；x86_64 generic include/asm-generic/cacheflush.h:23 → none
- 可疑调用位置：`exit_mmap` mm/mmap.c:3337（F3，第 3338 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、csky、m68k 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 11. 接口 `flush_ptrace_hw_breakpoint`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 7 个其他架构有实际实现（arm、arm64、loongarch、powerpc、sh、x86、xtensa）
- 各架构实现：riscv generic include/linux/hw_breakpoint.h:137 → none；arm64 arch arch/arm64/kernel/ptrace.c:207 → effect:barrier+mem（barrier+mem）；x86_64 arch arch/x86/kernel/hw_breakpoint.c:470 → effect:barrier+mem（barrier+mem）
- 可疑调用位置：`do_exit` kernel/exit.c:893（F3，第 896 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、loongarch 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 12. 接口 `gup_fast_permitted`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（mips、s390、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 无实现  → unknown；x86_64 arch arch/x86/include/asm/pgtable_64.h:260 → unknown
- 可疑调用位置：`gup_fast` mm/gup.c:3398（F3，第 3419 行使用）；`gup_fast` mm/gup.c:3398（F3，第 3419 行使用）；`gup_fast` mm/gup.c:3398（F2，第 3398 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 mips、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 13. 接口 `kvm_arch_flush_remote_tlbs`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、mips、x86）
- 各架构实现：riscv generic include/linux/kvm_host.h:1554 → none；arm64 arch arch/arm64/kvm/mmu.c:175 → effect:barrier+mem+tlb（barrier+mem+tlb）；x86_64 generic include/linux/kvm_host.h:1723 → none
- 可疑调用位置：`kvm_flush_remote_tlbs` virt/kvm/kvm_main.c:352（F3，第 353 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、mips、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 14. 接口 `kvm_arch_vcpu_ioctl_get_fpu`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（loongarch、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:310 → none；arm64 arch arch/arm64/kvm/guest.c:855 → none；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4555（F3，第 4571 行使用）；`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4555（F3，第 4559 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 loongarch、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 15. 接口 `kvm_arch_vcpu_ioctl_get_regs`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（loongarch、mips、powerpc、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:326 → none；arm64 arch arch/arm64/kvm/guest.c:536 → none；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4435（F3，第 4454 行使用）；`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4435（F3，第 4439 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 loongarch、mips、powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 16. 接口 `kvm_arch_vcpu_ioctl_get_sregs`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（powerpc、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:298 → none；arm64 arch arch/arm64/kvm/guest.c:736 → none；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4463（F3，第 4479 行使用）；`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4463（F3，第 4467 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 powerpc、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 17. 接口 `kvm_arch_vcpu_ioctl_set_fpu`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（loongarch、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:315 → none；arm64 arch arch/arm64/kvm/guest.c:860 → none；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4571（F3，第 4575 行使用）；`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4571（F3，第 4583 行使用）；`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4571（F2，第 4585 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 loongarch、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 18. 接口 `kvm_arch_vcpu_ioctl_set_regs`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（loongarch、mips、powerpc、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:331 → none；arm64 arch arch/arm64/kvm/guest.c:541 → none；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4454（F3，第 4463 行使用）；`kvm_vcpu_ioctl` virt/kvm/kvm_main.c:4454（F3，第 4455 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 loongarch、mips、powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 19. 接口 `kvm_arch_vcpu_precreate`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、s390、x86）
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:96 → none；arm64 arch arch/arm64/kvm/arm.c:526 → unknown；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_vm_ioctl_create_vcpu` virt/kvm/kvm_main.c:4220（F3，第 4222 行使用）；`kvm_vm_ioctl_create_vcpu` virt/kvm/kvm_main.c:4220（F3，第 4243 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 20. 接口 `pmd_soft_dirty`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 4 个其他架构有实际实现（mips、powerpc、s390、x86）
- 各架构实现：riscv generic include/linux/pgtable.h:1412 → none；arm64 generic include/linux/pgtable.h:1864 → none；x86_64 arch arch/x86/include/asm/pgtable.h:657 → unknown
- 可疑调用位置：`can_follow_write_pmd` mm/gup.c:774（F3，第 776 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 mips、powerpc、s390 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 21. 接口 `pte_needs_flush`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（parisc、powerpc、x86）
- 各架构实现：riscv generic include/asm-generic/tlb.h:738 → none；arm64 arch arch/arm64/include/asm/tlbflush.h:709 → unknown；x86_64 arch arch/x86/include/asm/tlbflush.h:445 → unknown
- 可疑调用位置：`change_pte_range` mm/mprotect.c:195（F3，第 198 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 parisc、powerpc、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 22. 接口 `ptrace_disable`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 14 个其他架构有实际实现（alpha、arm64、csky、hexagon、loongarch、m68k、mips、openrisc）
- 各架构实现：riscv arch arch/riscv/kernel/ptrace.c:293 → none；arm64 arch arch/arm64/kernel/ptrace.c:157 → effect（mem）；x86_64 arch arch/x86/kernel/ptrace.c:718 → effect（mem）
- 可疑调用位置：`ptrace_detach` kernel/ptrace.c:569（F3，第 576 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 23. 接口 `raw_pci_read`（Q-多数，5 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、loongarch、x86）
- 各架构实现：riscv arch arch/riscv/kernel/acpi.c:313 → none；arm64 arch arch/arm64/kernel/pci.c:14 → unknown；x86_64 arch arch/x86/pci/common.c:40 → unknown
- 可疑调用位置：`acpi_os_read_pci_configuration` drivers/acpi/osl.c:807（F3，第 808 行使用）；`acpi_os_read_pci_configuration` drivers/acpi/osl.c:807（F3，第 808 行使用）；`acpi_os_read_pci_configuration` drivers/acpi/osl.c:807（F3，第 808 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 24. 接口 `raw_pci_write`（Q-多数，6 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 3 个其他架构有实际实现（arm64、loongarch、x86）
- 各架构实现：riscv arch arch/riscv/kernel/acpi.c:319 → none；arm64 arch arch/arm64/kernel/pci.c:24 → unknown；x86_64 arch arch/x86/pci/common.c:50 → unknown
- 可疑调用位置：`acpi_os_write_pci_configuration` drivers/acpi/osl.c:835（F3，第 836 行使用）；`acpi_os_write_pci_configuration` drivers/acpi/osl.c:835（F3，第 836 行使用）；`acpi_os_write_pci_configuration` drivers/acpi/osl.c:835（F3，第 836 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 6.0

## 25. 接口 `user_disable_single_step`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 13 个其他架构有实际实现（alpha、arm64、csky、hexagon、loongarch、m68k、parisc、powerpc）
- 各架构实现：riscv generic include/linux/ptrace.h:301 → none；arm64 arch arch/arm64/kernel/debug-monitors.c:388 → effect（mem）；x86_64 arch arch/x86/kernel/step.c:229 → effect（mem）
- 可疑调用位置：`copy_process` kernel/fork.c:2448（F3，第 2449 行使用）；`ptrace_resume` kernel/ptrace.c:850（F3，第 862 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 5.6784

## 26. 接口 `arch_release_task_struct`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/kernel/process.c:176 → unknown；arm64 arch arch/arm64/kernel/process.c:344 → effect:mem（mem）；x86_64 arch arch/x86/kernel/process.c:118 → effect:mem（mem）
- 可疑调用位置：`free_task` kernel/fork.c:605（F3，第 606 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、s390、sh 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 27. 接口 `arch_tlbbatch_flush`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 barrier 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/mm/tlbflush.c:200 → effect（mem+tlb）；arm64 arch arch/arm64/include/asm/tlbflush.h:403 → effect:barrier+tlb（barrier+tlb）；x86_64 arch arch/x86/mm/tlb.c:1682 → effect（barrier+mem+tlb）
- 可疑调用位置：`try_to_unmap_flush` mm/rmap.c:650（F3，第 651 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 28. 接口 `huge_pte_modify`（Q-类别，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 的实现缺少 mem、pgtable 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv generic include/asm-generic/hugetlb.h:40 → unknown；arm64 generic include/asm-generic/hugetlb.h:35 → effect（mem+pgtable）；x86_64 generic include/asm-generic/hugetlb.h:35 → effect（mem+pgtable）
- 可疑调用位置：`hugetlb_change_protection` mm/hugetlb.c:6997（F3，第 7003 行使用）；`hugetlb_change_protection` mm/hugetlb.c:6997（F2，第 6998 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 s390 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 29. 接口 `set_direct_map_invalid_noflush`（Q-类别，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 的实现缺少 pgtable 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/mm/pageattr.c:377 → effect:mem+tlb（mem+tlb）；arm64 arch arch/arm64/mm/pageattr.c:254 → effect:mem+pgtable（mem+pgtable）；x86_64 arch arch/x86/mm/pat/set_memory.c:2659 → effect:mem+pgtable（mem+pgtable）
- 可疑调用位置：`secretmem_fault` mm/secretmem.c:77（F3，第 93 行使用）；`secretmem_fault` mm/secretmem.c:77（F2，第 80 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、s390、x86 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 30. 接口 `set_memory_x`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 barrier 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/mm/pageattr.c:367 → effect（mem+tlb）；arm64 arch arch/arm64/mm/pageattr.c:235 → effect（barrier+mem+tlb）；x86_64 arch arch/x86/mm/pat/set_memory.c:2317 → effect（barrier+cache+mem+pgtable+tlb）
- 可疑调用位置：`set_memory_rox` include/linux/set_memory.h:23（F3，第 23 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 31. 接口 `tlb_flush`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 barrier 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/include/asm/tlb.h:34 → effect:tlb（tlb）；arm64 arch arch/arm64/include/asm/tlb.h:53 → effect:barrier+tlb（barrier+tlb）；x86_64 arch arch/x86/include/asm/tlb.h:13 → effect（barrier+mem+tlb）
- 可疑调用位置：`tlb_flush_mmu_tlbonly` include/asm-generic/tlb.h:465（F3，第 466 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 32. 接口 `user_enable_single_step`（Q-类别，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv generic include/linux/ptrace.h:287 → unknown；arm64 arch arch/arm64/kernel/debug-monitors.c:379 → effect（mem）；x86_64 arch arch/x86/kernel/step.c:219 → effect（mem）
- 可疑调用位置：`ptrace_resume` kernel/ptrace.c:848（F3，第 850 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 33. 接口 `wrprotect_ptes`（Q-类别，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem、pgtable 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv generic include/linux/pgtable.h:840 → unknown；arm64 arch arch/arm64/include/asm/pgtable.h:1902 → effect:mem+pgtable+tlb（mem+pgtable+tlb）；x86_64 generic include/linux/pgtable.h:1115 → effect:mem+pgtable（mem+pgtable）
- 可疑调用位置：`__copy_present_ptes` mm/memory.c:943（F3，第 955 行使用）；`__copy_present_ptes` mm/memory.c:943（F3，第 955 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 4.0

## 34. 接口 `copy_from_kernel_nofault_allowed`（Q-多数，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 7 个其他架构有实际实现（arm、loongarch、mips、parisc、powerpc、um、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 无实现  → unknown；x86_64 arch arch/x86/mm/maccess.c:9 → unknown
- 可疑调用位置：`copy_from_kernel_nofault` mm/maccess.c:31（F3，第 36 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、loongarch、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.7856

## 35. 接口 `exit_thread`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（arm、mips、sparc、x86、xtensa）
- 各架构实现：riscv generic include/linux/sched/task.h:87 → none；arm64 generic include/linux/sched/task.h:90 → none；x86_64 arch arch/x86/kernel/process.c:128 → effect（mem）
- 可疑调用位置：`do_exit` kernel/exit.c:877（F3，第 885 行使用）；`copy_process` kernel/fork.c:2639（F3，第 2641 行使用）；`copy_process` kernel/fork.c:2639（F2，第 2639 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、mips、sparc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.7856

## 36. 接口 `flush_icache_pages`（Q-多数，4 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（alpha、m68k、nios2、parisc、sh）
- 各架构实现：riscv generic include/linux/cacheflush.h:21 → none；arm64 generic include/linux/cacheflush.h:21 → none；x86_64 generic include/linux/cacheflush.h:21 → none
- 可疑调用位置：`do_swap_page` mm/memory.c:4239（F3，第 4248 行使用）；`do_swap_page` mm/memory.c:4239（F3，第 4251 行使用）；`set_pte_range` mm/memory.c:4687（F3，第 4688 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、m68k、nios2 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.7856

## 37. 接口 `module_arch_cleanup`（Q-多数，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：riscv 没有实现或是空实现，而 7 个其他架构有实际实现（arc、arm、mips、parisc、s390、sh、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 无实现  → unknown；x86_64 arch arch/x86/kernel/module.c:309 → effect:mem（mem）
- 可疑调用位置：`free_module` kernel/module/main.c:1281（F3，第 1284 行使用）；`load_module` kernel/module/main.c:3028（F3，第 3030 行使用）；`load_module` kernel/module/main.c:3028（F2，第 3028 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arc、arm、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.7856

## 38. 接口 `pte_accessible`（Q-多数，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 没有实现或是空实现，而 5 个其他架构有实际实现（arm、arm64、loongarch、sparc、x86）
- 各架构实现：riscv 无实现  → unknown；arm64 无实现  → unknown；x86_64 arch arch/x86/include/asm/pgtable.h:965 → unknown
- 可疑调用位置：`ptep_clear_flush` mm/pgtable-generic.c:100（F3，第 102 行使用）；`set_tlb_ubc_flush_pending` mm/rmap.c:681（F3，第 684 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、loongarch 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.7856

## 39. 接口 `__cpu_up`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/smpboot.c:184 → effect:mem（mem）；arm64 arch arch/arm64/kernel/smp.c:113 → effect:barrier+mem（barrier+mem）；x86_64 无实现  → unknown
- 可疑调用位置：`bringup_cpu` kernel/cpu.c:867（F3，第 871 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arc、arm 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 40. 接口 `__get_wchan`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2、F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/stacktrace.c:148 → effect（mem）；arm64 arch arch/arm64/kernel/process.c:796 → effect（mem）；x86_64 arch arch/x86/kernel/process.c:1041 → effect（mem）
- 可疑调用位置：`get_wchan` kernel/sched/core.c:2099（F3，第 2100 行使用）；`get_wchan` kernel/sched/core.c:2099（F2，第 2102 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arc、arm 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 41. 接口 `arch_dup_task_struct`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/process.c:183 → effect（mem）；arm64 arch arch/arm64/kernel/process.c:349 → effect（mem）；x86_64 arch arch/x86/kernel/process.c:105 → effect（mem）
- 可疑调用位置：`dup_task_struct` kernel/fork.c:1111（F3，第 1115 行使用）；`dup_task_struct` kernel/fork.c:1111（F3，第 1147 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 42. 接口 `arch_stack_walk`（Q-类别，4 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：riscv 的实现缺少 mem 类效果，arm64 和 x86_64 的实现都有
- 各架构实现：riscv arch arch/riscv/kernel/stacktrace.c:159 → unknown；arm64 arch arch/arm64/kernel/stacktrace.c:381 → effect:mem（mem）；x86_64 arch arch/x86/kernel/stacktrace.c:15 → effect:mem（mem）
- 可疑调用位置：`stack_trace_save` kernel/stacktrace.c:122（F3，第 123 行使用）；`stack_trace_save_tsk` kernel/stacktrace.c:150（F3，第 152 行使用）；`stack_trace_save_tsk` kernel/stacktrace.c:150（F3，第 151 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、loongarch 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 43. 接口 `clock_getres_fallback`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/include/asm/vdso/gettimeofday.h:54 → effect；arm64 arch arch/arm64/include/asm/vdso/gettimeofday.h:58 → effect；x86_64 arch arch/x86/include/asm/vdso/gettimeofday.h:71 → effect
- 可疑调用位置：`__cvdso_clock_getres_data` lib/vdso/gettimeofday.c:421（F3，第 421 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 44. 接口 `clock_gettime_fallback`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/include/asm/vdso/gettimeofday.h:38 → effect；arm64 arch arch/arm64/include/asm/vdso/gettimeofday.h:41 → effect；x86_64 arch arch/x86/include/asm/vdso/gettimeofday.h:58 → effect
- 可疑调用位置：`__cvdso_clock_gettime_data` lib/vdso/gettimeofday.c:278（F3，第 278 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm、arm64、csky 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 45. 接口 `copy_thread`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kernel/process.c:195 → effect（mem）；arm64 arch arch/arm64/kernel/process.c:413 → effect（mem）；x86_64 arch arch/x86/kernel/process.c:170 → effect（mem）
- 可疑调用位置：`copy_process` kernel/fork.c:2399（F3，第 2403 行使用）；`copy_process` kernel/fork.c:2399（F3，第 2406 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arc、arm 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 46. 接口 `futex_atomic_cmpxchg_inatomic`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/include/asm/futex.h:76 → effect（mem）；arm64 arch arch/arm64/include/asm/futex.h:285 → effect（mem）；x86_64 arch arch/x86/include/asm/futex.h:77 → effect（mem）
- 可疑调用位置：`futex_cmpxchg_value_locked` kernel/futex/core.c:458（F2，第 461 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 alpha、arc、arm 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 47. 接口 `huge_ptep_modify_prot_commit`（未定性，3 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv generic include/linux/hugetlb.h:1012 → effect（cache+mem+pgtable+tlb）；arm64 arch arch/arm64/mm/hugetlbpage.c:533 → effect（barrier+mem+pgtable+tlb）；x86_64 generic include/linux/hugetlb.h:1066 → effect（mem+pgtable）
- 可疑调用位置：`hugetlb_change_protection` mm/hugetlb.c:7003（F3，第 7023 行使用）；`hugetlb_change_protection` mm/hugetlb.c:7003（F3，第 7009 行使用）；`hugetlb_change_protection` mm/hugetlb.c:7003（F3，第 7009 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 48. 接口 `huge_ptep_set_wrprotect`（未定性，2 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/mm/hugetlbpage.c:309 → effect（cache+mem+pgtable+tlb）；arm64 arch arch/arm64/mm/hugetlbpage.c:453 → effect（barrier+mem+pgtable+tlb）；x86_64 generic include/asm-generic/hugetlb.h:101 → effect:mem+pgtable（mem+pgtable）
- 可疑调用位置：`copy_hugetlb_page_range` mm/hugetlb.c:5529（F3，第 5544 行使用）；`copy_hugetlb_page_range` mm/hugetlb.c:5529（F3，第 5536 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、parisc、powerpc 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 49. 接口 `kprobe_fault_handler`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv generic include/linux/kprobes.h:453 → none；arm64 generic include/linux/kprobes.h:445 → none；x86_64 arch arch/x86/kernel/kprobes/core.c:1030 → effect（mem）
- 可疑调用位置：`kprobe_page_fault` include/linux/kprobes.h:600（F3，第 600 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arc、arm、arm64 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

## 50. 接口 `kvm_arch_init_vm`（未定性，1 处调用）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：横向比对不成立
- 各架构实现：riscv arch arch/riscv/kvm/vm.c:30 → effect（mem+pgtable+tlb）；arm64 arch arch/arm64/kvm/arm.c:222 → effect（mem+register）；x86_64 无实现  → unknown
- 可疑调用位置：`kvm_create_vm` virt/kvm/kvm_main.c:1216（F3，第 1225 行使用）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照 arm64、loongarch、mips 的实现，看公共层依赖的效果在 riscv 上由谁保证
- 得分 3.0

