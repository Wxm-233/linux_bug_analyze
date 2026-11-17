# 人工分析建议：A380

接口 3200 个；候选 4903 个（F1 1481、F2 348、F3 4555）；横向定性成立 54 个。以下为前 50 条。

## 1. `kprobe_page_fault` 调用 `kprobe_fault_handler`（include/linux/kprobes.h:591）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 591 行被直接使用（return），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/linux/kprobes.h:444 → none；arm64 generic include/linux/kprobes.h:445 → none；x86_64 arch arch/x86/kernel/kprobes/core.c:1030 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 9.0（别的架构修过此处）

## 2. `perf_misc_flags` 调用 `perf_arch_guest_misc_flags`（kernel/events/core.c:7719）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 7719 行被直接使用（return），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/linux/perf_event.h:1834 → none；arm64 generic include/linux/perf_event.h:1820 → none；x86_64 arch arch/x86/events/core.c:3126 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 9.0（别的架构修过此处）

## 3. `dup_mmap` 调用 `arch_dup_mmap`（mm/mmap.c:1849）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `oldmm` 在第 1854 行被直接使用（arg，传给 `ksm_fork`），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv（横向定性成立）
- 各架构实现：riscv generic include/asm-generic/mm_hooks.h:10 → none；arm64 arch arch/arm64/include/asm/mmu_context.h:185 → unknown；x86_64 arch arch/x86/include/asm/mmu_context.h:218 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv 上是否由别处保证
- 得分 9.0（别的架构修过此处）

## 4. `dup_mmap` 调用 `arch_dup_mmap`（mm/mmap.c:1849）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 2 个实参 `mm` 在第 1854 行被直接使用（arg，传给 `ksm_fork`），其间没有检查；产生效果的架构：arm64、x86_64；不产生效果的架构：riscv（横向定性成立）
- 各架构实现：riscv generic include/asm-generic/mm_hooks.h:10 → none；arm64 arch arch/arm64/include/asm/mmu_context.h:185 → effect；x86_64 arch arch/x86/include/asm/mmu_context.h:218 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64、x86_64 的实现，看公共层依赖的效果在 riscv 上是否由别处保证
- 得分 9.0（别的架构修过此处）

## 5. `kvm_vm_ioctl_enable_cap_generic` 调用 `kvm_vm_ioctl_enable_cap`（virt/kvm/kvm_main.c:5095）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 5095 行被直接使用（return），其间没有检查；产生效果的架构：arm64；不产生效果的架构：riscv（横向定性成立）
- 各架构实现：riscv arch arch/riscv/kvm/vm.c:212 → none；arm64 arch arch/arm64/kvm/arm.c:135 → effect；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64 的实现，看公共层依赖的效果在 riscv 上是否由别处保证
- 得分 9.0（别的架构修过此处）

## 6. `kvm_vm_ioctl` 调用 `kvm_arch_vm_ioctl`（virt/kvm/kvm_main.c:5387）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：调用后 返回值 在第 5390 行被直接使用（return），其间没有检查；产生效果的架构：arm64；不产生效果的架构：riscv（横向定性成立）
- 各架构实现：riscv arch arch/riscv/kvm/vm.c:225 → none；arm64 arch arch/arm64/kvm/arm.c:2034 → effect；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64 的实现，看公共层依赖的效果在 riscv 上是否由别处保证
- 得分 9.0（别的架构修过此处）

## 7. `cpc_write` 调用 `cpc_write_ffh`（drivers/acpi/cppc_acpi.c:1117）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 1117 行被直接使用（return），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：arm64（横向定性成立）
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kernel/topology.c:548 → none；x86_64 arch arch/x86/kernel/acpi/cppc.c:63 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 arm64 上是否由别处保证
- 得分 6.0

## 8. `hugepage_migration_supported` 调用 `arch_hugetlb_migration_supported`（include/linux/hugetlb.h:909）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 909 行被直接使用（return），其间没有检查；产生效果的架构：riscv、arm64；不产生效果的架构：x86_64（横向定性成立）
- 各架构实现：riscv arch arch/riscv/mm/hugetlbpage.c:434 → effect；arm64 arch arch/arm64/mm/hugetlbpage.c:65 → effect；x86_64 generic include/linux/hugetlb.h:898 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64 的实现，看公共层依赖的效果在 x86_64 上是否由别处保证
- 得分 6.0

## 9. `hypervisor_isolated_pci_functions` 调用 `jailhouse_paravirt`（include/linux/hypervisor.h:43）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 43 行被直接使用（return），其间没有检查；产生效果的架构：riscv、arm64；不产生效果的架构：x86_64（横向定性成立）
- 各架构实现：riscv generic include/linux/hypervisor.h:28 → effect；arm64 generic include/linux/hypervisor.h:28 → effect；x86_64 arch arch/x86/include/asm/jailhouse_para.h:20 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64 的实现，看公共层依赖的效果在 x86_64 上是否由别处保证
- 得分 6.0

## 10. `resilient_queued_spin_lock_slowpath` 调用 `resilient_virt_spin_lock`（kernel/bpf/rqspinlock.c:349）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 349 行被直接使用（return），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/asm-generic/rqspinlock.h:53 → none；arm64 generic include/asm-generic/rqspinlock.h:53 → none；x86_64 arch arch/x86/include/asm/rqspinlock.h:24 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 6.0

## 11. `ptrace_detach` 调用 `ptrace_disable`（kernel/ptrace.c:569）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `child` 在第 576 行被直接使用（member），其间没有检查；产生效果的架构：arm64、x86_64；不产生效果的架构：riscv（横向定性成立）
- 各架构实现：riscv arch arch/riscv/kernel/ptrace.c:540 → none；arm64 arch arch/arm64/kernel/ptrace.c:157 → effect；x86_64 arch arch/x86/kernel/ptrace.c:718 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64、x86_64 的实现，看公共层依赖的效果在 riscv 上是否由别处保证
- 得分 6.0

## 12. `__clocksource_register_scale` 调用 `clocksource_arch_init`（kernel/time/clocksource.c:1240）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `cs` 在第 1242 行被直接使用（member），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/linux/clocksource.h:274 → none；arm64 generic include/linux/clocksource.h:301 → none；x86_64 arch arch/x86/kernel/time.c:101 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 6.0

## 13. `do_mmap` 调用 `execute_only_pkey`（mm/mmap.c:392）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `mm` 在第 402 行被直接使用（member），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：arm64（横向定性成立）
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/include/asm/pkeys.h:36 → none；x86_64 arch arch/x86/include/asm/pkeys.h:24 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 arm64 上是否由别处保证
- 得分 6.0

## 14. `should_defer_flush` 调用 `arch_tlbbatch_should_defer`（mm/rmap.c:785）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 785 行被直接使用（return），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv arch arch/riscv/mm/tlbflush.c:225 → none；arm64 arch arch/arm64/include/asm/tlbflush.h:388 → none；x86_64 arch arch/x86/include/asm/tlbflush.h:355 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 6.0

## 15. `kvm_vcpu_ioctl` 调用 `kvm_arch_vcpu_run_pid_change`（virt/kvm/kvm_main.c:4464）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `vcpu` 在第 4469 行被直接使用（member），其间没有检查；产生效果的架构：arm64；不产生效果的架构：riscv、x86_64（横向定性成立）
- 各架构实现：riscv generic include/linux/kvm_host.h:2445 → none；arm64 arch arch/arm64/kvm/arm.c:926 → effect；x86_64 generic include/linux/kvm_host.h:2492 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64 的实现，看公共层依赖的效果在 riscv、x86_64 上是否由别处保证
- 得分 6.0

## 16. `copy_process` 调用 `user_disable_single_step`（kernel/fork.c:2284）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `p` 在第 2285 行被直接使用（member），其间没有检查；产生效果的架构：arm64、x86_64；不产生效果的架构：riscv（横向定性成立）
- 各架构实现：riscv generic include/linux/ptrace.h:301 → none；arm64 arch arch/arm64/kernel/debug-monitors.c:388 → effect；x86_64 arch arch/x86/kernel/step.c:229 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64、x86_64 的实现，看公共层依赖的效果在 riscv 上是否由别处保证
- 得分 5.6784（别的架构修过此处）

## 17. `ptrace_resume` 调用 `user_disable_single_step`（kernel/ptrace.c:850）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `child` 在第 862 行被直接使用（member），其间没有检查；产生效果的架构：arm64、x86_64；不产生效果的架构：riscv（横向定性成立）
- 各架构实现：riscv generic include/linux/ptrace.h:301 → none；arm64 arch arch/arm64/kernel/debug-monitors.c:388 → effect；x86_64 arch arch/x86/kernel/step.c:229 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64、x86_64 的实现，看公共层依赖的效果在 riscv 上是否由别处保证
- 得分 5.6784（别的架构修过此处）

## 18. `is_kernel_text` 调用 `in_gate_area_no_mm`（include/linux/kallsyms.h:31）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 31 行被直接使用（return），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/linux/mm.h:4458 → none；arm64 generic include/linux/mm.h:5117 → none；x86_64 arch arch/x86/entry/vsyscall/vsyscall_64.c:350 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 3.7856

## 19. `is_kernel` 调用 `in_gate_area_no_mm`（include/linux/kallsyms.h:38）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 38 行被直接使用（return），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/linux/mm.h:4458 → none；arm64 generic include/linux/mm.h:5117 → none；x86_64 arch arch/x86/entry/vsyscall/vsyscall_64.c:350 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 3.7856

## 20. `perf_copy_attr` 调用 `perf_reg_validate`（kernel/events/core.c:13603）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：调用后 返回值 在第 13623 行被直接使用（return），其间没有检查；产生效果的架构：arm64；不产生效果的架构：riscv、x86_64（横向定性成立）
- 各架构实现：riscv arch arch/riscv/kernel/perf_regs.c:21 → none；arm64 arch arch/arm64/kernel/perf_regs.c:80 → effect；x86_64 arch arch/x86/kernel/perf_regs.c:115 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64 的实现，看公共层依赖的效果在 riscv、x86_64 上是否由别处保证
- 得分 3.7856

## 21. `do_exit` 调用 `exit_thread`（kernel/exit.c:977）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F1、F3
- 依据：调用后 第 1 个实参 `tsk` 在第 979 行被直接使用（arg，传给 `sched_autogroup_exit_task`），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/linux/sched/task.h:89 → none；arm64 generic include/linux/sched/task.h:90 → none；x86_64 arch arch/x86/kernel/process.c:128 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 3.7856

## 22. `__mmdrop` 调用 `destroy_context`（kernel/fork.c:729）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F1、F3
- 依据：调用后 第 1 个实参 `mm` 在第 730 行被直接使用（arg，传给 `mmu_notifier_subscriptions_destroy`），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/asm-generic/mmu_context.h:46 → none；arm64 generic include/asm-generic/mmu_context.h:46 → none；x86_64 arch arch/x86/include/asm/mmu_context.h:172 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 3.7856

## 23. `mm_init` 调用 `destroy_context`（kernel/fork.c:1139）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `mm` 在第 1141 行被直接使用（arg，传给 `mm_free_id`），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/asm-generic/mmu_context.h:46 → none；arm64 generic include/asm-generic/mmu_context.h:46 → none；x86_64 arch arch/x86/include/asm/mmu_context.h:172 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 3.7856

## 24. `copy_process` 调用 `exit_thread`（kernel/fork.c:2493）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `p` 在第 2495 行被直接使用（member），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：riscv、arm64（横向定性成立）
- 各架构实现：riscv generic include/linux/sched/task.h:89 → none；arm64 generic include/linux/sched/task.h:90 → none；x86_64 arch arch/x86/kernel/process.c:128 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 3.7856

## 25. `update_vsyscall` 调用 `__arch_update_vdso_clock`（kernel/time/vsyscall.c:121）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `vc` 在第 122 行被直接使用（deref），其间没有检查；产生效果的架构：arm64；不产生效果的架构：riscv、x86_64（横向定性成立）
- 各架构实现：riscv generic include/asm-generic/vdso/vsyscall.h:22 → none；arm64 arch arch/arm64/include/asm/vdso/vsyscall.h:16 → effect；x86_64 generic include/asm-generic/vdso/vsyscall.h:22 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64 的实现，看公共层依赖的效果在 riscv、x86_64 上是否由别处保证
- 得分 3.7856

## 26. `add_hugetlb_folio` 调用 `arch_clear_hugetlb_flags`（mm/hugetlb.c:1507）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `folio` 在第 1508 行被直接使用（arg，传给 `enqueue_hugetlb_folio`），其间没有检查；产生效果的架构：riscv、arm64；不产生效果的架构：x86_64（横向定性成立）
- 各架构实现：riscv arch arch/riscv/include/asm/hugetlb.h:8 → effect；arm64 arch arch/arm64/include/asm/hugetlb.h:22 → effect；x86_64 generic include/linux/hugetlb.h:845 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64 的实现，看公共层依赖的效果在 x86_64 上是否由别处保证
- 得分 3.7856

## 27. `free_huge_folio` 调用 `arch_clear_hugetlb_flags`（mm/hugetlb.c:1799）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `folio` 在第 1800 行被直接使用（arg，传给 `enqueue_hugetlb_folio`），其间没有检查；产生效果的架构：riscv、arm64；不产生效果的架构：x86_64（横向定性成立）
- 各架构实现：riscv arch arch/riscv/include/asm/hugetlb.h:8 → effect；arm64 arch arch/arm64/include/asm/hugetlb.h:22 → effect；x86_64 generic include/linux/hugetlb.h:845 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64 的实现，看公共层依赖的效果在 x86_64 上是否由别处保证
- 得分 3.7856

## 28. `syscall_enter_from_user_mode_work` 调用 `syscall_trace_enter`（include/linux/entry-common.h:156）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：调用后 返回值 在第 158 行被直接使用（return），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv generic include/linux/entry-common.h:81 → effect；arm64 arch arch/arm64/kernel/ptrace.c:2461 → effect；x86_64 generic include/linux/entry-common.h:65 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 29. `start_kernel` 调用 `setup_arch`（init/main.c:1030）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `command_line` 在第 1037 行被直接使用（arg，传给 `setup_command_line`），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/setup.c:316 → effect；arm64 arch arch/arm64/kernel/setup.c:281 → effect；x86_64 arch arch/x86/kernel/setup.c:884 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 30. `perf_misc_flags` 调用 `perf_arch_guest_misc_flags`（kernel/events/core.c:7719）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `regs` 在第 7721 行被直接使用（member），其间没有检查；产生效果的架构：无；不产生效果的架构：riscv、arm64
- 各架构实现：riscv generic include/linux/perf_event.h:1834 → none；arm64 generic include/linux/perf_event.h:1820 → none；x86_64 arch arch/x86/events/core.c:3126 → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照各架构实现，看公共层依赖的效果在 riscv、arm64 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 31. `prepare_uprobe` 调用 `arch_uprobe_analyze_insn`（kernel/events/uprobes.c:1117）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `uprobe` 在第 1122 行被直接使用（member），其间没有检查；产生效果的架构：riscv、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/probes/uprobes.c:31 → effect；arm64 无实现  → unknown；x86_64 arch arch/x86/kernel/uprobes.c:1626 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 32. `prepare_uretprobe` 调用 `arch_uretprobe_hijack_return_addr`（kernel/events/uprobes.c:2271）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 2 个实参 `regs` 在第 2277 行被直接使用（arg，传给 `cleanup_return_instances`），其间没有检查；产生效果的架构：riscv；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/probes/uprobes.c:130 → effect；arm64 无实现  → unknown；x86_64 arch arch/x86/kernel/uprobes.c:1851 → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 33. `task_struct_whitelist` 调用 `arch_thread_struct_whitelist`（kernel/fork.c:837）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `offset` 在第 844 行被直接使用（deref），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/include/asm/processor.h:129 → effect；arm64 arch arch/arm64/include/asm/processor.h:269 → effect；x86_64 arch arch/x86/include/asm/processor.h:545 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 34. `task_struct_whitelist` 调用 `arch_thread_struct_whitelist`（kernel/fork.c:837）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 2 个实参 `size` 在第 843 行被直接使用（deref），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/include/asm/processor.h:129 → effect；arm64 arch arch/arm64/include/asm/processor.h:269 → effect；x86_64 arch arch/x86/include/asm/processor.h:545 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 35. `dup_task_struct` 调用 `arch_dup_task_struct`（kernel/fork.c:920）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `tsk` 在第 924 行被直接使用（arg，传给 `alloc_thread_stack_node`），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/process.c:214 → effect；arm64 arch arch/arm64/kernel/process.c:349 → effect；x86_64 arch arch/x86/kernel/process.c:105 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 36. `dup_task_struct` 调用 `arch_dup_task_struct`（kernel/fork.c:920）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 2 个实参 `orig` 在第 956 行被直接使用（member），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/process.c:214 → unknown；arm64 arch arch/arm64/kernel/process.c:349 → unknown；x86_64 arch arch/x86/kernel/process.c:105 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 37. `copy_process` 调用 `copy_thread`（kernel/fork.c:2232）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `p` 在第 2236 行被直接使用（arg，传给 `stackleak_task_init`），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/process.c:238 → effect；arm64 arch arch/arm64/kernel/process.c:413 → effect；x86_64 arch arch/x86/kernel/process.c:170 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 38. `copy_process` 调用 `copy_thread`（kernel/fork.c:2232）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 2 个实参 `args` 在第 2239 行被直接使用（member），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/process.c:238 → unknown；arm64 arch arch/arm64/kernel/process.c:413 → unknown；x86_64 arch arch/x86/kernel/process.c:170 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 39. `futex_cmpxchg_value_locked` 调用 `futex_atomic_cmpxchg_inatomic`（kernel/futex/futex.h:278）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：调用后 返回值 在第 281 行被直接使用（return），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/include/asm/futex.h:76 → effect；arm64 arch arch/arm64/include/asm/futex.h:285 → effect；x86_64 arch arch/x86/include/asm/futex.h:77 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 40. `flush_module_icache` 调用 `flush_icache_range`（kernel/module/main.c:2843）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `mod_mem` 在第 2844 行被直接使用（member），其间没有检查；产生效果的架构：无；不产生效果的架构：x86_64
- 各架构实现：riscv arch arch/riscv/include/asm/cacheflush.h:81 → unknown；arm64 arch arch/arm64/include/asm/cacheflush.h:84 → unknown；x86_64 generic include/asm-generic/cacheflush.h:71 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照各架构实现，看公共层依赖的效果在 x86_64 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 41. `flush_module_icache` 调用 `flush_icache_range`（kernel/module/main.c:2843）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 2 个实参 `mod_mem` 在第 2844 行被直接使用（member），其间没有检查；产生效果的架构：无；不产生效果的架构：x86_64
- 各架构实现：riscv arch arch/riscv/include/asm/cacheflush.h:81 → unknown；arm64 arch arch/arm64/include/asm/cacheflush.h:84 → unknown；x86_64 generic include/asm-generic/cacheflush.h:71 → none
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照各架构实现，看公共层依赖的效果在 x86_64 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 42. `layout_and_allocate` 调用 `module_frob_arch_sections`（kernel/module/main.c:2889）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `info` 在第 2890 行被直接使用（member），其间没有检查；产生效果的架构：无；不产生效果的架构：无
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kernel/module-plts.c:280 → unknown；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照各架构实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 43. `layout_and_allocate` 调用 `module_frob_arch_sections`（kernel/module/main.c:2889）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 2 个实参 `info` 在第 2890 行被直接使用（member），其间没有检查；产生效果的架构：无；不产生效果的架构：无
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kernel/module-plts.c:280 → unknown；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照各架构实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 44. `layout_and_allocate` 调用 `module_frob_arch_sections`（kernel/module/main.c:2889）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 3 个实参 `info` 在第 2890 行被直接使用（member），其间没有检查；产生效果的架构：无；不产生效果的架构：无
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kernel/module-plts.c:280 → unknown；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照各架构实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 45. `layout_and_allocate` 调用 `module_frob_arch_sections`（kernel/module/main.c:2889）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 4 个实参 `info` 在第 2890 行被直接使用（member），其间没有检查；产生效果的架构：arm64；不产生效果的架构：无
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/kernel/module-plts.c:280 → effect；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 46. `post_relocation` 调用 `module_finalize`（kernel/module/main.c:2960）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 返回值 在第 2960 行被直接使用（return），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/module.c:895 → effect；arm64 arch arch/arm64/kernel/module.c:484 → effect；x86_64 arch arch/x86/kernel/module.c:226 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 47. `__find_resource_space` 调用 `arch_remove_reservations`（kernel/resource.c:752）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `tmp` 在第 755 行被直接使用（member），其间没有检查；产生效果的架构：x86_64；不产生效果的架构：无
- 各架构实现：riscv 无实现  → unknown；arm64 无实现  → unknown；x86_64 arch arch/x86/kernel/resource.c:60 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 48. `get_wchan` 调用 `__get_wchan`（kernel/sched/core.c:2089）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `p` 在第 2090 行被直接使用（member），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/stacktrace.c:168 → effect；arm64 arch arch/arm64/kernel/process.c:796 → effect；x86_64 arch arch/x86/kernel/process.c:1041 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 49. `get_wchan` 调用 `__get_wchan`（kernel/sched/core.c:2089）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F2
- 依据：调用后 返回值 在第 2092 行被直接使用（return），其间没有检查；产生效果的架构：riscv、arm64、x86_64；不产生效果的架构：无
- 各架构实现：riscv arch arch/riscv/kernel/stacktrace.c:168 → effect；arm64 arch arch/arm64/kernel/process.c:796 → effect；x86_64 arch arch/x86/kernel/process.c:1041 → effect
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照riscv、arm64、x86_64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

## 50. `__do_sys_prctl` 调用 `arch_set_shadow_stack_status`（kernel/sys.c:2871）

- 可能的缺陷类型：效果依赖（实现一致性检查）；形态 F3
- 依据：调用后 第 1 个实参 `me` 在第 2876 行被直接使用（arg，传给 `arch_lock_shadow_stack_status`），其间没有检查；产生效果的架构：arm64；不产生效果的架构：无
- 各架构实现：riscv 无实现  → unknown；arm64 arch arch/arm64/mm/gcs.c:159 → effect；x86_64 无实现  → unknown
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：对照arm64 的实现，看公共层依赖的效果在 其他架构 上是否由别处保证
- 得分 3.0（别的架构修过此处）

