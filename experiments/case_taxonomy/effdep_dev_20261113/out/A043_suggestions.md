# 人工分析建议：A043

接口 3223 个；候选 4092 个（F1 1287、F2 295、F3 3797）；横向定性成立 51 个。以下为前 50 条。

## 1. `kprobe_page_fault` 调用 `kprobe_fault_handler`（include/linux/kprobes.h:593）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 593 行被直接使用（return），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/linux/kprobes.h:449 → none；arm64 generic include/linux/kprobes.h:445 → none；x86_64 arch arch/x86/kernel/kprobes/core.c:1030 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 9.0（别的架构修过此处）

## 2. `dup_mmap` 调用 `arch_dup_mmap`（kernel/fork.c:756）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `oldmm` 在第 774 行被直接使用（arg，传给 `flush_tlb_mm`），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv（横向定性成立）
- 各架构实现：riscv generic include/asm-generic/mm_hooks.h:10 → none；arm64 arch arch/arm64/include/asm/mmu_context.h:185 → unknown；x86_64 arch arch/x86/include/asm/mmu_context.h:218 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv 上是否由别处保证
- 得分 9.0（别的架构修过此处）

## 3. `dup_mmap` 调用 `arch_dup_mmap`（kernel/fork.c:756）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 2 个实参 `mm` 在第 773 行被直接使用（arg，传给 `mmap_write_unlock`），其间没有检查；产生效果的架构：arm64、x86_64；不产生效果的架构：riscv（横向定性成立）
- 各架构实现：riscv generic include/asm-generic/mm_hooks.h:10 → none；arm64 arch arch/arm64/include/asm/mmu_context.h:185 → effect；x86_64 arch arch/x86/include/asm/mmu_context.h:218 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64、x86_64 的实现，看公共层依赖的效果在 riscv 上是否由别处保证
- 得分 9.0（别的架构修过此处）

## 4. `kvm_vcpu_ioctl` 调用 `kvm_arch_vcpu_ioctl_set_guest_debug`（virt/kvm/kvm_main.c:4542）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `vcpu` 在第 4565 行被直接使用（arg，传给 `kvm_vcpu_ioctl_set_sigmask`），其间没有检查；产生效果的架构：arm64；不产生效果的架构：riscv（横向定性成立）
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:475 → none；arm64 arch arch/arm64/kvm/guest.c:881 → effect；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64 的实现，看公共层依赖的效果在 riscv 上是否由别处保证
- 得分 9.0（别的架构修过此处）

## 5. `kvm_vm_ioctl` 调用 `kvm_arch_vm_ioctl`（virt/kvm/kvm_main.c:5325）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：调用后 返回值 在第 5328 行被直接使用（return），其间没有检查；产生效果的架构：arm64；不产生效果的架构：riscv（横向定性成立）
- 各架构实现：riscv arch arch/riscv/kvm/vm.c:211 → none；arm64 arch arch/arm64/kvm/arm.c:2034 → effect；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64 的实现，看公共层依赖的效果在 riscv 上是否由别处保证
- 得分 9.0（别的架构修过此处）

## 6. `hugepage_migration_supported` 调用 `arch_hugetlb_migration_supported`（include/linux/hugetlb.h:924）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 924 行被直接使用（return），其间没有检查；产生效果的架构：riscv、arm64；不产生效果的架构：x86_64（横向定性成立）
- 各架构实现：riscv arch arch/riscv/mm/hugetlbpage.c:429 → effect；arm64 arch arch/arm64/mm/hugetlbpage.c:65 → effect；x86_64 generic include/linux/hugetlb.h:898 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64 的实现，看公共层依赖的效果在 x86_64 上是否由别处保证
- 得分 6.0

## 7. `hypervisor_isolated_pci_functions` 调用 `jailhouse_paravirt`（include/linux/hypervisor.h:40）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 40 行被直接使用（return），其间没有检查；产生效果的架构：riscv、arm64；不产生效果的架构：x86_64（横向定性成立）
- 各架构实现：riscv generic include/linux/hypervisor.h:28 → effect；arm64 generic include/linux/hypervisor.h:28 → effect；x86_64 arch arch/x86/include/asm/jailhouse_para.h:20 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64 的实现，看公共层依赖的效果在 x86_64 上是否由别处保证
- 得分 6.0

## 8. `mm_release` 调用 `deactivate_mm`（kernel/fork.c:1620）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `tsk` 在第 1627 行被直接使用（member），其间没有检查；产生效果的架构：arm64；不产生效果的架构：riscv（横向定性成立）
- 各架构实现：riscv generic include/asm-generic/mmu_context.h:70 → none；arm64 arch arch/arm64/include/asm/mmu_context.h:317 → effect；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64 的实现，看公共层依赖的效果在 riscv 上是否由别处保证
- 得分 6.0

## 9. `ptrace_detach` 调用 `ptrace_disable`（kernel/ptrace.c:572）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `child` 在第 579 行被直接使用（member），其间没有检查；产生效果的架构：arm64、x86_64；不产生效果的架构：riscv（横向定性成立）
- 各架构实现：riscv arch arch/riscv/kernel/ptrace.c:293 → none；arm64 arch arch/arm64/kernel/ptrace.c:157 → effect；x86_64 arch arch/x86/kernel/ptrace.c:718 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64、x86_64 的实现，看公共层依赖的效果在 riscv 上是否由别处保证
- 得分 6.0

## 10. `__clocksource_register_scale` 调用 `clocksource_arch_init`（kernel/time/clocksource.c:1190）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `cs` 在第 1192 行被直接使用（member），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/linux/clocksource.h:267 → none；arm64 generic include/linux/clocksource.h:301 → none；x86_64 arch arch/x86/kernel/time.c:101 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 6.0

## 11. `do_mmap` 调用 `execute_only_pkey`（mm/mmap.c:1265）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `mm` 在第 1275 行被直接使用（member），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：arm64（横向定性成立）
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/include/asm/pkeys.h:36 → none；x86_64 arch arch/x86/include/asm/pkeys.h:24 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 arm64 上是否由别处保证
- 得分 6.0

## 12. `should_defer_flush` 调用 `arch_tlbbatch_should_defer`（mm/rmap.c:725）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 725 行被直接使用（return），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv arch arch/riscv/mm/tlbflush.c:216 → none；arm64 arch arch/arm64/include/asm/tlbflush.h:388 → none；x86_64 arch arch/x86/include/asm/tlbflush.h:355 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 6.0

## 13. `kvm_vm_ioctl_create_vcpu` 调用 `kvm_arch_vcpu_postcreate`（virt/kvm/kvm_main.c:4310）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `vcpu` 在第 4311 行被直接使用（arg，传给 `kvm_create_vcpu_debugfs`），其间没有检查；产生效果的架构：riscv；不产生效果的架构：arm64（横向定性成立）
- 各架构实现：riscv arch arch/riscv/kvm/vcpu.c:158 → effect；arm64 arch arch/arm64/kvm/arm.c:585 → none；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv 的实现，看公共层依赖的效果在 arm64 上是否由别处保证
- 得分 6.0

## 14. `kvm_vcpu_ioctl` 调用 `kvm_arch_vcpu_run_pid_change`（virt/kvm/kvm_main.c:4431）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `vcpu` 在第 4436 行被直接使用（member），其间没有检查；产生效果的架构：arm64；不产生效果的架构：riscv、x86_64（横向定性成立）
- 各架构实现：riscv generic include/linux/kvm_host.h:2294 → none；arm64 arch arch/arm64/kvm/arm.c:926 → effect；x86_64 generic include/linux/kvm_host.h:2492 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64 的实现，看公共层依赖的效果在 riscv、x86_64 上是否由别处保证
- 得分 6.0

## 15. `copy_process` 调用 `user_disable_single_step`（kernel/fork.c:2552）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `p` 在第 2553 行被直接使用（member），其间没有检查；产生效果的架构：arm64、x86_64；不产生效果的架构：riscv（横向定性成立）
- 各架构实现：riscv generic include/linux/ptrace.h:301 → none；arm64 arch arch/arm64/kernel/debug-monitors.c:388 → effect；x86_64 arch arch/x86/kernel/step.c:229 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64、x86_64 的实现，看公共层依赖的效果在 riscv 上是否由别处保证
- 得分 5.6784（别的架构修过此处）

## 16. `ptrace_resume` 调用 `user_disable_single_step`（kernel/ptrace.c:853）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `child` 在第 865 行被直接使用（member），其间没有检查；产生效果的架构：arm64、x86_64；不产生效果的架构：riscv（横向定性成立）
- 各架构实现：riscv generic include/linux/ptrace.h:301 → none；arm64 arch arch/arm64/kernel/debug-monitors.c:388 → effect；x86_64 arch arch/x86/kernel/step.c:229 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64、x86_64 的实现，看公共层依赖的效果在 riscv 上是否由别处保证
- 得分 5.6784（别的架构修过此处）

## 17. `is_kernel_text` 调用 `in_gate_area_no_mm`（include/linux/kallsyms.h:31）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 31 行被直接使用（return），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/linux/mm.h:3809 → none；arm64 generic include/linux/mm.h:5117 → none；x86_64 arch arch/x86/entry/vsyscall/vsyscall_64.c:350 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 3.7856

## 18. `is_kernel` 调用 `in_gate_area_no_mm`（include/linux/kallsyms.h:38）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 38 行被直接使用（return），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/linux/mm.h:3809 → none；arm64 generic include/linux/mm.h:5117 → none；x86_64 arch arch/x86/entry/vsyscall/vsyscall_64.c:350 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 3.7856

## 19. `perf_copy_attr` 调用 `perf_reg_validate`（kernel/events/core.c:12221）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：调用后 返回值 在第 12241 行被直接使用（return），其间没有检查；产生效果的架构：arm64；不产生效果的架构：riscv、x86_64（横向定性成立）
- 各架构实现：riscv arch arch/riscv/kernel/perf_regs.c:21 → none；arm64 arch arch/arm64/kernel/perf_regs.c:80 → effect；x86_64 arch arch/x86/kernel/perf_regs.c:115 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64 的实现，看公共层依赖的效果在 riscv、x86_64 上是否由别处保证
- 得分 3.7856

## 20. `do_exit` 调用 `exit_thread`（kernel/exit.c:872）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F1、F3
- 依据：调用后 第 1 个实参 `tsk` 在第 880 行被直接使用（arg，传给 `perf_event_exit_task`），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/linux/sched/task.h:87 → none；arm64 generic include/linux/sched/task.h:90 → none；x86_64 arch arch/x86/kernel/process.c:128 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 3.7856

## 21. `__mmdrop` 调用 `destroy_context`（kernel/fork.c:918）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F1、F3
- 依据：调用后 第 1 个实参 `mm` 在第 919 行被直接使用（arg，传给 `mmu_notifier_subscriptions_destroy`），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/asm-generic/mmu_context.h:46 → none；arm64 generic include/asm-generic/mmu_context.h:46 → none；x86_64 arch arch/x86/include/asm/mmu_context.h:172 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 3.7856

## 22. `mm_init` 调用 `destroy_context`（kernel/fork.c:1312）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `mm` 在第 1314 行被直接使用（arg，传给 `mm_free_pgd`），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/asm-generic/mmu_context.h:46 → none；arm64 generic include/asm-generic/mmu_context.h:46 → none；x86_64 arch arch/x86/include/asm/mmu_context.h:172 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 3.7856

## 23. `copy_process` 调用 `exit_thread`（kernel/fork.c:2743）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `p` 在第 2745 行被直接使用（member），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/linux/sched/task.h:87 → none；arm64 generic include/linux/sched/task.h:90 → none；x86_64 arch arch/x86/kernel/process.c:128 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 3.7856

## 24. `pmd_huge_tests` 调用 `pmd_clear_huge`（mm/debug_vm_pgtable.c:449）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `args` 在第 450 行被直接使用（member），其间没有检查；产生效果的架构：riscv、arm64；不产生效果的架构：x86_64（横向定性成立）
- 各架构实现：riscv arch arch/riscv/mm/pgtable.c:105 → effect；arm64 arch arch/arm64/mm/mmu.c:1907 → effect；x86_64 arch arch/x86/mm/pgtable.c:697 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64 的实现，看公共层依赖的效果在 x86_64 上是否由别处保证
- 得分 3.7856

## 25. `pud_huge_tests` 调用 `pud_clear_huge`（mm/debug_vm_pgtable.c:469）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `args` 在第 470 行被直接使用（member），其间没有检查；产生效果的架构：riscv、arm64；不产生效果的架构：x86_64（横向定性成立）
- 各架构实现：riscv arch arch/riscv/mm/pgtable.c:67 → effect；arm64 arch arch/arm64/mm/mmu.c:1899 → effect；x86_64 arch arch/x86/mm/pgtable.c:681 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64 的实现，看公共层依赖的效果在 x86_64 上是否由别处保证
- 得分 3.7856

## 26. `syscall_enter_from_user_mode_work` 调用 `syscall_trace_enter`（include/linux/entry-common.h:168）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 2 个实参 `syscall` 在第 170 行被直接使用（return），其间没有检查；产生效果的架构：无；不产生效果的架构：无
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kernel/ptrace.c:2461 → unknown；x86_64 generic include/linux/entry-common.h:65 → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照各架构实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 27. `syscall_enter_from_user_mode_work` 调用 `syscall_trace_enter`（include/linux/entry-common.h:168）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：调用后 返回值 在第 170 行被直接使用（return），其间没有检查；产生效果的架构：arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kernel/ptrace.c:2461 → effect；x86_64 generic include/linux/entry-common.h:65 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 28. `start_kernel` 调用 `setup_arch`（init/main.c:897）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `command_line` 在第 899 行被直接使用（arg，传给 `setup_command_line`），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/setup.c:249 → effect；arm64 arch arch/arm64/kernel/setup.c:281 → effect；x86_64 arch arch/x86/kernel/setup.c:884 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 29. `bringup_cpu` 调用 `__cpu_up`（kernel/cpu.c:868）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `cpu` 在第 872 行被直接使用（arg，传给 `cpuhp_bp_sync_alive`），其间没有检查；产生效果的架构：无；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/smpboot.c:189 → unknown；arm64 arch arch/arm64/kernel/smp.c:113 → unknown；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照各架构实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 30. `dup_task_struct` 调用 `arch_dup_task_struct`（kernel/fork.c:1108）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `tsk` 在第 1112 行被直接使用（arg，传给 `alloc_thread_stack_node`），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/process.c:185 → effect；arm64 arch arch/arm64/kernel/process.c:349 → effect；x86_64 arch arch/x86/kernel/process.c:105 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 31. `dup_task_struct` 调用 `arch_dup_task_struct`（kernel/fork.c:1108）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 2 个实参 `orig` 在第 1144 行被直接使用（member），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/process.c:185 → unknown；arm64 arch arch/arm64/kernel/process.c:349 → unknown；x86_64 arch arch/x86/kernel/process.c:105 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 32. `copy_process` 调用 `copy_thread`（kernel/fork.c:2505）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `p` 在第 2509 行被直接使用（arg，传给 `stackleak_task_init`），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/process.c:197 → effect；arm64 arch arch/arm64/kernel/process.c:413 → effect；x86_64 arch arch/x86/kernel/process.c:170 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 33. `copy_process` 调用 `copy_thread`（kernel/fork.c:2505）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 2 个实参 `args` 在第 2512 行被直接使用（member），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/process.c:197 → unknown；arm64 arch arch/arm64/kernel/process.c:413 → unknown；x86_64 arch arch/x86/kernel/process.c:170 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 34. `futex_cmpxchg_value_locked` 调用 `futex_atomic_cmpxchg_inatomic`（kernel/futex/core.c:458）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：调用后 返回值 在第 461 行被直接使用（return），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/include/asm/futex.h:76 → effect；arm64 arch arch/arm64/include/asm/futex.h:285 → effect；x86_64 arch arch/x86/include/asm/futex.h:77 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 35. `layout_and_allocate` 调用 `module_frob_arch_sections`（kernel/module/main.c:2373）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `info` 在第 2374 行被直接使用（member），其间没有检查；产生效果的架构：无；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/module-sections.c:90 → unknown；arm64 arch arch/arm64/kernel/module-plts.c:280 → unknown；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照各架构实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 36. `layout_and_allocate` 调用 `module_frob_arch_sections`（kernel/module/main.c:2373）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 2 个实参 `info` 在第 2374 行被直接使用（member），其间没有检查；产生效果的架构：无；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/module-sections.c:90 → unknown；arm64 arch arch/arm64/kernel/module-plts.c:280 → unknown；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照各架构实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 37. `layout_and_allocate` 调用 `module_frob_arch_sections`（kernel/module/main.c:2373）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 3 个实参 `info` 在第 2374 行被直接使用（member），其间没有检查；产生效果的架构：无；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/module-sections.c:90 → unknown；arm64 arch arch/arm64/kernel/module-plts.c:280 → unknown；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照各架构实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 38. `layout_and_allocate` 调用 `module_frob_arch_sections`（kernel/module/main.c:2373）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 4 个实参 `info` 在第 2374 行被直接使用（member），其间没有检查；产生效果的架构：riscv、arm64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/module-sections.c:90 → effect；arm64 arch arch/arm64/kernel/module-plts.c:280 → effect；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 39. `post_relocation` 调用 `module_finalize`（kernel/module/main.c:2452）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 2452 行被直接使用（return），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/module.c:919 → effect；arm64 arch arch/arm64/kernel/module.c:484 → effect；x86_64 arch arch/x86/kernel/module.c:226 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 40. `__find_resource` 调用 `arch_remove_reservations`（kernel/resource.c:661）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `tmp` 在第 664 行被直接使用（member），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：无
- 各架构实现：riscv 无实现  → unknown；arm64 无实现  → unknown；x86_64 arch arch/x86/kernel/resource.c:60 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 41. `get_wchan` 调用 `__get_wchan`（kernel/sched/core.c:2101）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `p` 在第 2102 行被直接使用（member），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/stacktrace.c:140 → effect；arm64 arch arch/arm64/kernel/process.c:796 → effect；x86_64 arch arch/x86/kernel/process.c:1041 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 42. `get_wchan` 调用 `__get_wchan`（kernel/sched/core.c:2101）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：调用后 返回值 在第 2104 行被直接使用（return），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/stacktrace.c:140 → effect；arm64 arch arch/arm64/kernel/process.c:796 → effect；x86_64 arch arch/x86/kernel/process.c:1041 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 43. `memcpy_from_iter_mc` 调用 `copy_mc_to_kernel`（lib/iov_iter.c:251）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 251 行被直接使用（return），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv generic include/linux/uaccess.h:201 → effect；arm64 generic include/linux/uaccess.h:239 → effect；x86_64 arch arch/x86/lib/copy_mc.c:63 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 44. `__cvdso_clock_gettime_data` 调用 `clock_gettime_fallback`（lib/vdso/gettimeofday.c:261）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 261 行被直接使用（return），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/include/asm/vdso/gettimeofday.h:38 → effect；arm64 arch arch/arm64/include/asm/vdso/gettimeofday.h:41 → effect；x86_64 arch arch/x86/include/asm/vdso/gettimeofday.h:58 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 45. `__cvdso_clock_getres_data` 调用 `clock_getres_fallback`（lib/vdso/gettimeofday.c:404）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 404 行被直接使用（return），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/include/asm/vdso/gettimeofday.h:54 → effect；arm64 arch arch/arm64/include/asm/vdso/gettimeofday.h:58 → effect；x86_64 arch arch/x86/include/asm/vdso/gettimeofday.h:71 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 46. `get_gate_page` 调用 `get_gate_vma`（mm/gup.c:895）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：调用后 返回值 在第 898 行被直接使用（deref），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/linux/mm.h:3805 → none；arm64 generic include/linux/mm.h:5113 → none；x86_64 arch arch/x86/entry/vsyscall/vsyscall_64.c:324 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 3.0

## 47. `copy_hugetlb_page_range` 调用 `huge_ptep_set_wrprotect`（mm/hugetlb.c:5461）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `src` 在第 5476 行被直接使用（member），其间没有检查；产生效果的架构：riscv、arm64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/mm/hugetlbpage.c:309 → effect；arm64 arch arch/arm64/mm/hugetlbpage.c:453 → effect；x86_64 generic include/asm-generic/hugetlb.h:101 → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 48. `copy_hugetlb_page_range` 调用 `huge_ptep_set_wrprotect`（mm/hugetlb.c:5461）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 2 个实参 `addr` 在第 5468 行被直接使用（arg，传给 `set_huge_pte_at`），其间没有检查；产生效果的架构：riscv、arm64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/mm/hugetlbpage.c:309 → effect；arm64 arch arch/arm64/mm/hugetlbpage.c:453 → effect；x86_64 generic include/asm-generic/hugetlb.h:101 → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 49. `hugetlb_change_protection` 调用 `huge_ptep_modify_prot_commit`（mm/hugetlb.c:6962）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `vma` 在第 6982 行被直接使用（arg，传给 `flush_tlb_range`），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv generic include/linux/hugetlb.h:1019 → effect；arm64 arch arch/arm64/mm/hugetlbpage.c:533 → effect；x86_64 generic include/linux/hugetlb.h:1066 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 50. `hugetlb_change_protection` 调用 `huge_ptep_modify_prot_commit`（mm/hugetlb.c:6962）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 2 个实参 `address` 在第 6968 行被直接使用（arg，传给 `set_huge_pte_at`），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv generic include/linux/hugetlb.h:1019 → effect；arm64 arch arch/arm64/mm/hugetlbpage.c:533 → effect；x86_64 generic include/linux/hugetlb.h:1066 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

