# 人工分析建议：B485

接口 3206 个；候选 4489 个（F1 1400、F2 339、F3 4150）；横向定性成立 58 个。以下为前 50 条。

## 1. `kprobe_page_fault` 调用 `kprobe_fault_handler`（include/linux/kprobes.h:591）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 591 行被直接使用（return），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/linux/kprobes.h:444 → none；arm64 generic include/linux/kprobes.h:445 → none；x86_64 arch arch/x86/kernel/kprobes/core.c:1030 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 9.0（别的架构修过此处）

## 2. `perf_misc_flags` 调用 `perf_arch_guest_misc_flags`（kernel/events/core.c:7012）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 7012 行被直接使用（return），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/linux/perf_event.h:1693 → none；arm64 generic include/linux/perf_event.h:1820 → none；x86_64 arch arch/x86/events/core.c:3126 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 9.0（别的架构修过此处）

## 3. `dup_mmap` 调用 `arch_dup_mmap`（kernel/fork.c:759）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `oldmm` 在第 764 行被直接使用（arg，传给 `ksm_fork`），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv（横向定性成立）
- 各架构实现：riscv generic include/asm-generic/mm_hooks.h:10 → none；arm64 arch arch/arm64/include/asm/mmu_context.h:185 → unknown；x86_64 arch arch/x86/include/asm/mmu_context.h:218 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv 上是否由别处保证
- 得分 9.0（别的架构修过此处）

## 4. `dup_mmap` 调用 `arch_dup_mmap`（kernel/fork.c:759）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 2 个实参 `mm` 在第 764 行被直接使用（arg，传给 `ksm_fork`），其间没有检查；产生效果的架构：arm64、x86_64；不产生效果的架构：riscv（横向定性成立）
- 各架构实现：riscv generic include/asm-generic/mm_hooks.h:10 → none；arm64 arch arch/arm64/include/asm/mmu_context.h:185 → effect；x86_64 arch arch/x86/include/asm/mmu_context.h:218 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64、x86_64 的实现，看公共层依赖的效果在 riscv 上是否由别处保证
- 得分 9.0（别的架构修过此处）

## 5. `kvm_vm_ioctl` 调用 `kvm_arch_vm_ioctl`（virt/kvm/kvm_main.c:5241）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：调用后 返回值 在第 5244 行被直接使用（return），其间没有检查；产生效果的架构：arm64；不产生效果的架构：riscv（横向定性成立）
- 各架构实现：riscv arch arch/riscv/kvm/vm.c:212 → none；arm64 arch arch/arm64/kvm/arm.c:2034 → effect；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64 的实现，看公共层依赖的效果在 riscv 上是否由别处保证
- 得分 9.0（别的架构修过此处）

## 6. `cpc_write` 调用 `cpc_write_ffh`（drivers/acpi/cppc_acpi.c:1114）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 1114 行被直接使用（return），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：arm64（横向定性成立）
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kernel/topology.c:548 → none；x86_64 arch arch/x86/kernel/acpi/cppc.c:63 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 arm64 上是否由别处保证
- 得分 6.0

## 7. `hugepage_migration_supported` 调用 `arch_hugetlb_migration_supported`（include/linux/hugetlb.h:865）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 865 行被直接使用（return），其间没有检查；产生效果的架构：riscv、arm64；不产生效果的架构：x86_64（横向定性成立）
- 各架构实现：riscv arch arch/riscv/mm/hugetlbpage.c:420 → effect；arm64 arch arch/arm64/mm/hugetlbpage.c:65 → effect；x86_64 generic include/linux/hugetlb.h:898 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64 的实现，看公共层依赖的效果在 x86_64 上是否由别处保证
- 得分 6.0

## 8. `hypervisor_isolated_pci_functions` 调用 `jailhouse_paravirt`（include/linux/hypervisor.h:40）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 40 行被直接使用（return），其间没有检查；产生效果的架构：riscv、arm64；不产生效果的架构：x86_64（横向定性成立）
- 各架构实现：riscv generic include/linux/hypervisor.h:28 → effect；arm64 generic include/linux/hypervisor.h:28 → effect；x86_64 arch arch/x86/include/asm/jailhouse_para.h:20 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64 的实现，看公共层依赖的效果在 x86_64 上是否由别处保证
- 得分 6.0

## 9. `mm_release` 调用 `deactivate_mm`（kernel/fork.c:1630）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `tsk` 在第 1637 行被直接使用（member），其间没有检查；产生效果的架构：arm64；不产生效果的架构：riscv（横向定性成立）
- 各架构实现：riscv generic include/asm-generic/mmu_context.h:70 → none；arm64 arch arch/arm64/include/asm/mmu_context.h:317 → effect；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64 的实现，看公共层依赖的效果在 riscv 上是否由别处保证
- 得分 6.0

## 10. `ptrace_detach` 调用 `ptrace_disable`（kernel/ptrace.c:569）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `child` 在第 576 行被直接使用（member），其间没有检查；产生效果的架构：arm64、x86_64；不产生效果的架构：riscv（横向定性成立）
- 各架构实现：riscv arch arch/riscv/kernel/ptrace.c:335 → none；arm64 arch arch/arm64/kernel/ptrace.c:157 → effect；x86_64 arch arch/x86/kernel/ptrace.c:718 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64、x86_64 的实现，看公共层依赖的效果在 riscv 上是否由别处保证
- 得分 6.0

## 11. `__clocksource_register_scale` 调用 `clocksource_arch_init`（kernel/time/clocksource.c:1245）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `cs` 在第 1247 行被直接使用（member），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/linux/clocksource.h:274 → none；arm64 generic include/linux/clocksource.h:301 → none；x86_64 arch arch/x86/kernel/time.c:101 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 6.0

## 12. `do_mmap` 调用 `execute_only_pkey`（mm/mmap.c:338）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `mm` 在第 348 行被直接使用（member），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：arm64（横向定性成立）
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/include/asm/pkeys.h:36 → none；x86_64 arch arch/x86/include/asm/pkeys.h:24 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 arm64 上是否由别处保证
- 得分 6.0

## 13. `should_defer_flush` 调用 `arch_tlbbatch_should_defer`（mm/rmap.c:724）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 724 行被直接使用（return），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv arch arch/riscv/mm/tlbflush.c:183 → none；arm64 arch arch/arm64/include/asm/tlbflush.h:388 → none；x86_64 arch arch/x86/include/asm/tlbflush.h:355 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 6.0

## 14. `kvm_vcpu_ioctl` 调用 `kvm_arch_vcpu_run_pid_change`（virt/kvm/kvm_main.c:4328）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `vcpu` 在第 4333 行被直接使用（member），其间没有检查；产生效果的架构：arm64；不产生效果的架构：riscv、x86_64（横向定性成立）
- 各架构实现：riscv generic include/linux/kvm_host.h:2422 → none；arm64 arch arch/arm64/kvm/arm.c:926 → effect；x86_64 generic include/linux/kvm_host.h:2492 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64 的实现，看公共层依赖的效果在 riscv、x86_64 上是否由别处保证
- 得分 6.0

## 15. `copy_process` 调用 `user_disable_single_step`（kernel/fork.c:2453）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `p` 在第 2454 行被直接使用（member），其间没有检查；产生效果的架构：arm64、x86_64；不产生效果的架构：riscv（横向定性成立）
- 各架构实现：riscv generic include/linux/ptrace.h:301 → none；arm64 arch arch/arm64/kernel/debug-monitors.c:388 → effect；x86_64 arch arch/x86/kernel/step.c:229 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64、x86_64 的实现，看公共层依赖的效果在 riscv 上是否由别处保证
- 得分 5.6784（别的架构修过此处）

## 16. `ptrace_resume` 调用 `user_disable_single_step`（kernel/ptrace.c:850）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `child` 在第 862 行被直接使用（member），其间没有检查；产生效果的架构：arm64、x86_64；不产生效果的架构：riscv（横向定性成立）
- 各架构实现：riscv generic include/linux/ptrace.h:301 → none；arm64 arch arch/arm64/kernel/debug-monitors.c:388 → effect；x86_64 arch arch/x86/kernel/step.c:229 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64、x86_64 的实现，看公共层依赖的效果在 riscv 上是否由别处保证
- 得分 5.6784（别的架构修过此处）

## 17. `is_kernel_text` 调用 `in_gate_area_no_mm`（include/linux/kallsyms.h:31）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 31 行被直接使用（return），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/linux/mm.h:3800 → none；arm64 generic include/linux/mm.h:5117 → none；x86_64 arch arch/x86/entry/vsyscall/vsyscall_64.c:350 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 3.7856

## 18. `is_kernel` 调用 `in_gate_area_no_mm`（include/linux/kallsyms.h:38）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 38 行被直接使用（return），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/linux/mm.h:3800 → none；arm64 generic include/linux/mm.h:5117 → none；x86_64 arch arch/x86/entry/vsyscall/vsyscall_64.c:350 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 3.7856

## 19. `perf_copy_attr` 调用 `perf_reg_validate`（kernel/events/core.c:12522）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：调用后 返回值 在第 12542 行被直接使用（return），其间没有检查；产生效果的架构：arm64；不产生效果的架构：riscv、x86_64（横向定性成立）
- 各架构实现：riscv arch arch/riscv/kernel/perf_regs.c:21 → none；arm64 arch arch/arm64/kernel/perf_regs.c:80 → effect；x86_64 arch arch/x86/kernel/perf_regs.c:115 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64 的实现，看公共层依赖的效果在 riscv、x86_64 上是否由别处保证
- 得分 3.7856

## 20. `do_exit` 调用 `exit_thread`（kernel/exit.c:939）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F1、F3
- 依据：调用后 第 1 个实参 `tsk` 在第 947 行被直接使用（arg，传给 `perf_event_exit_task`），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/linux/sched/task.h:88 → none；arm64 generic include/linux/sched/task.h:90 → none；x86_64 arch arch/x86/kernel/process.c:128 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 3.7856

## 21. `__mmdrop` 调用 `destroy_context`（kernel/fork.c:926）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F1、F3
- 依据：调用后 第 1 个实参 `mm` 在第 927 行被直接使用（arg，传给 `mmu_notifier_subscriptions_destroy`），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/asm-generic/mmu_context.h:46 → none；arm64 generic include/asm-generic/mmu_context.h:46 → none；x86_64 arch arch/x86/include/asm/mmu_context.h:172 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 3.7856

## 22. `mm_init` 调用 `destroy_context`（kernel/fork.c:1321）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `mm` 在第 1323 行被直接使用（arg，传给 `mm_free_pgd`），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/asm-generic/mmu_context.h:46 → none；arm64 generic include/asm-generic/mmu_context.h:46 → none；x86_64 arch arch/x86/include/asm/mmu_context.h:172 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 3.7856

## 23. `copy_process` 调用 `exit_thread`（kernel/fork.c:2647）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `p` 在第 2649 行被直接使用（member），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/linux/sched/task.h:88 → none；arm64 generic include/linux/sched/task.h:90 → none；x86_64 arch arch/x86/kernel/process.c:128 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 3.7856

## 24. `pmd_huge_tests` 调用 `pmd_clear_huge`（mm/debug_vm_pgtable.c:443）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `args` 在第 444 行被直接使用（member），其间没有检查；产生效果的架构：riscv、arm64；不产生效果的架构：x86_64（横向定性成立）
- 各架构实现：riscv arch arch/riscv/mm/pgtable.c:118 → effect；arm64 arch arch/arm64/mm/mmu.c:1907 → effect；x86_64 arch arch/x86/mm/pgtable.c:697 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64 的实现，看公共层依赖的效果在 x86_64 上是否由别处保证
- 得分 3.7856

## 25. `pud_huge_tests` 调用 `pud_clear_huge`（mm/debug_vm_pgtable.c:463）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `args` 在第 464 行被直接使用（member），其间没有检查；产生效果的架构：riscv、arm64；不产生效果的架构：x86_64（横向定性成立）
- 各架构实现：riscv arch arch/riscv/mm/pgtable.c:80 → effect；arm64 arch arch/arm64/mm/mmu.c:1899 → effect；x86_64 arch arch/x86/mm/pgtable.c:681 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64 的实现，看公共层依赖的效果在 x86_64 上是否由别处保证
- 得分 3.7856

## 26. `add_hugetlb_folio` 调用 `arch_clear_hugetlb_flags`（mm/hugetlb.c:1652）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `folio` 在第 1653 行被直接使用（arg，传给 `enqueue_hugetlb_folio`），其间没有检查；产生效果的架构：riscv、arm64；不产生效果的架构：x86_64（横向定性成立）
- 各架构实现：riscv arch arch/riscv/include/asm/hugetlb.h:8 → effect；arm64 arch arch/arm64/include/asm/hugetlb.h:22 → effect；x86_64 generic include/linux/hugetlb.h:845 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64 的实现，看公共层依赖的效果在 x86_64 上是否由别处保证
- 得分 3.7856

## 27. `free_huge_folio` 调用 `arch_clear_hugetlb_flags`（mm/hugetlb.c:1943）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `folio` 在第 1944 行被直接使用（arg，传给 `enqueue_hugetlb_folio`），其间没有检查；产生效果的架构：riscv、arm64；不产生效果的架构：x86_64（横向定性成立）
- 各架构实现：riscv arch arch/riscv/include/asm/hugetlb.h:8 → effect；arm64 arch arch/arm64/include/asm/hugetlb.h:22 → effect；x86_64 generic include/linux/hugetlb.h:845 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64 的实现，看公共层依赖的效果在 x86_64 上是否由别处保证
- 得分 3.7856

## 28. `syscall_enter_from_user_mode_work` 调用 `syscall_trace_enter`（include/linux/entry-common.h:169）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 2 个实参 `syscall` 在第 171 行被直接使用（return），其间没有检查；产生效果的架构：无；不产生效果的架构：无
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kernel/ptrace.c:2461 → unknown；x86_64 generic include/linux/entry-common.h:65 → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照各架构实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 29. `syscall_enter_from_user_mode_work` 调用 `syscall_trace_enter`（include/linux/entry-common.h:169）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：调用后 返回值 在第 171 行被直接使用（return），其间没有检查；产生效果的架构：arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kernel/ptrace.c:2461 → effect；x86_64 generic include/linux/entry-common.h:65 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 30. `start_kernel` 调用 `setup_arch`（init/main.c:922）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `command_line` 在第 928 行被直接使用（arg，传给 `setup_command_line`），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/setup.c:285 → effect；arm64 arch arch/arm64/kernel/setup.c:281 → effect；x86_64 arch arch/x86/kernel/setup.c:884 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 31. `bringup_cpu` 调用 `__cpu_up`（kernel/cpu.c:877）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `cpu` 在第 881 行被直接使用（arg，传给 `cpuhp_bp_sync_alive`），其间没有检查；产生效果的架构：无；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/smpboot.c:182 → unknown；arm64 arch arch/arm64/kernel/smp.c:113 → unknown；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照各架构实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 32. `perf_misc_flags` 调用 `perf_arch_guest_misc_flags`（kernel/events/core.c:7012）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `regs` 在第 7014 行被直接使用（member），其间没有检查；产生效果的架构：无；不产生效果的架构：riscv、arm64
- 各架构实现：riscv generic include/linux/perf_event.h:1693 → none；arm64 generic include/linux/perf_event.h:1820 → none；x86_64 arch arch/x86/events/core.c:3126 → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照各架构实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 33. `dup_task_struct` 调用 `arch_dup_task_struct`（kernel/fork.c:1117）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `tsk` 在第 1121 行被直接使用（arg，传给 `alloc_thread_stack_node`），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/process.c:197 → effect；arm64 arch arch/arm64/kernel/process.c:349 → effect；x86_64 arch arch/x86/kernel/process.c:105 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 34. `dup_task_struct` 调用 `arch_dup_task_struct`（kernel/fork.c:1117）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 2 个实参 `orig` 在第 1153 行被直接使用（member），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/process.c:197 → unknown；arm64 arch arch/arm64/kernel/process.c:349 → unknown；x86_64 arch arch/x86/kernel/process.c:105 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 35. `copy_process` 调用 `copy_thread`（kernel/fork.c:2404）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `p` 在第 2408 行被直接使用（arg，传给 `stackleak_task_init`），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/process.c:209 → effect；arm64 arch arch/arm64/kernel/process.c:413 → effect；x86_64 arch arch/x86/kernel/process.c:170 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 36. `copy_process` 调用 `copy_thread`（kernel/fork.c:2404）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 2 个实参 `args` 在第 2411 行被直接使用（member），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/process.c:209 → unknown；arm64 arch arch/arm64/kernel/process.c:413 → unknown；x86_64 arch arch/x86/kernel/process.c:170 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 37. `futex_cmpxchg_value_locked` 调用 `futex_atomic_cmpxchg_inatomic`（kernel/futex/futex.h:236）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：调用后 返回值 在第 239 行被直接使用（return），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/include/asm/futex.h:76 → effect；arm64 arch arch/arm64/include/asm/futex.h:285 → effect；x86_64 arch arch/x86/include/asm/futex.h:77 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 38. `layout_and_allocate` 调用 `module_frob_arch_sections`（kernel/module/main.c:2717）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `info` 在第 2718 行被直接使用（member），其间没有检查；产生效果的架构：无；不产生效果的架构：无
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kernel/module-plts.c:280 → unknown；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照各架构实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 39. `layout_and_allocate` 调用 `module_frob_arch_sections`（kernel/module/main.c:2717）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 2 个实参 `info` 在第 2718 行被直接使用（member），其间没有检查；产生效果的架构：无；不产生效果的架构：无
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kernel/module-plts.c:280 → unknown；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照各架构实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 40. `layout_and_allocate` 调用 `module_frob_arch_sections`（kernel/module/main.c:2717）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 3 个实参 `info` 在第 2718 行被直接使用（member），其间没有检查；产生效果的架构：无；不产生效果的架构：无
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kernel/module-plts.c:280 → unknown；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照各架构实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 41. `layout_and_allocate` 调用 `module_frob_arch_sections`（kernel/module/main.c:2717）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 4 个实参 `info` 在第 2718 行被直接使用（member），其间没有检查；产生效果的架构：arm64；不产生效果的架构：无
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kernel/module-plts.c:280 → effect；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 42. `post_relocation` 调用 `module_finalize`（kernel/module/main.c:2807）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `info` 在第 2824 行被直接使用（member），其间没有检查；产生效果的架构：无；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/module.c:905 → unknown；arm64 arch arch/arm64/kernel/module.c:484 → unknown；x86_64 arch arch/x86/kernel/module.c:226 → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照各架构实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 43. `post_relocation` 调用 `module_finalize`（kernel/module/main.c:2807）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 2 个实参 `info` 在第 2824 行被直接使用（member），其间没有检查；产生效果的架构：无；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/module.c:905 → unknown；arm64 arch arch/arm64/kernel/module.c:484 → unknown；x86_64 arch arch/x86/kernel/module.c:226 → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照各架构实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 44. `post_relocation` 调用 `module_finalize`（kernel/module/main.c:2807）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 3 个实参 `mod` 在第 2812 行被直接使用（member），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/module.c:905 → unknown；arm64 arch arch/arm64/kernel/module.c:484 → unknown；x86_64 arch arch/x86/kernel/module.c:226 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 45. `__find_resource_space` 调用 `arch_remove_reservations`（kernel/resource.c:696）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `tmp` 在第 699 行被直接使用（member），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：无
- 各架构实现：riscv 无实现  → unknown；arm64 无实现  → unknown；x86_64 arch arch/x86/kernel/resource.c:60 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 46. `get_wchan` 调用 `__get_wchan`（kernel/sched/core.c:2050）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `p` 在第 2051 行被直接使用（member），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/stacktrace.c:149 → effect；arm64 arch arch/arm64/kernel/process.c:796 → effect；x86_64 arch arch/x86/kernel/process.c:1041 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 47. `get_wchan` 调用 `__get_wchan`（kernel/sched/core.c:2050）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：调用后 返回值 在第 2053 行被直接使用（return），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/stacktrace.c:149 → effect；arm64 arch arch/arm64/kernel/process.c:796 → effect；x86_64 arch arch/x86/kernel/process.c:1041 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 48. `__cvdso_clock_gettime_data` 调用 `clock_gettime_fallback`（lib/vdso/gettimeofday.c:278）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 278 行被直接使用（return），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/include/asm/vdso/gettimeofday.h:38 → effect；arm64 arch arch/arm64/include/asm/vdso/gettimeofday.h:41 → effect；x86_64 arch arch/x86/include/asm/vdso/gettimeofday.h:58 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 49. `__cvdso_clock_getres_data` 调用 `clock_getres_fallback`（lib/vdso/gettimeofday.c:421）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 421 行被直接使用（return），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/include/asm/vdso/gettimeofday.h:54 → effect；arm64 arch arch/arm64/include/asm/vdso/gettimeofday.h:58 → effect；x86_64 arch arch/x86/include/asm/vdso/gettimeofday.h:71 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 50. `get_gate_page` 调用 `get_gate_vma`（mm/gup.c:1133）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：调用后 返回值 在第 1136 行被直接使用（deref），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/linux/mm.h:3796 → none；arm64 generic include/linux/mm.h:5113 → none；x86_64 arch arch/x86/entry/vsyscall/vsyscall_64.c:324 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 3.0

