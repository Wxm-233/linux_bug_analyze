# 当前版本 riscv：纵向候选人工核对

修订 2 之后，共有 32 个候选，其中有横向差异的 2 个。按判据核对的是这 2 个；其余 30 个作为额外参考也看了，单独列出。判断标准见修订 1 第 3 条。核对人 Claude，读的是 `/root/repos/linux`（7.3-rc2）。

## 有横向差异的（判据要求核对的）

| 排名 | 位置 | 接口 | 标志 | 被跳过的调用 | 判断 | 理由 |
|---|---|---|---|---|---|---|
| 3 | `hugetlb_fault` mm/hugetlb.c:6132 | `update_mmu_cache` | `ret = 0` | vma_end_read | 不是 | ret = 0 是返回码，随后 goto out_mutex；vma_end_read 是释放锁，与 update_mmu_cache 的效果无关 |
| 4 | `hugetlb_fault` mm/hugetlb.c:6132 | `update_mmu_cache_range` | `ret = 0` | vma_end_read | 不是 | 同上 |

## 其余候选（额外参考）

| 排名 | 位置 | 接口 | 标志 | 被跳过的调用 | 判断 | 理由 |
|---|---|---|---|---|---|---|
| 1 | `acpi_os_read_memory` drivers/acpi/osl.c:758 | `acpi_os_ioremap` | `unmap = true` | rcu_read_unlock | 不是 | unmap = true 记录映射来源，之后对称释放 |
| 2 | `acpi_os_write_memory` drivers/acpi/osl.c:789 | `acpi_os_ioremap` | `unmap = true` | rcu_read_unlock | 不是 | 同上 |
| 5 | `do_swap_page` mm/memory.c:5175 | `pte_modify` | `rwp_restore = true` | do_wp_page | 真实依赖，当前满足 | 调用 pte_modify(pte, PAGE_NONE) 后置 rwp_restore = true，跳过 do_wp_page（写时复制），依赖 pte_modify 保留 _PAGE_UFFD 位（源码注释写明）。支持 USERFAULTFD_RWP 的三个架构（x86 明确把 _PAGE_UFFD 放进 _PAGE_CHG_MASK；arm64、riscv 的掩码保留权限位以外的所有位）都满足。2026-07 的 763f43865fc4 修过同一类依赖在其他路径上的缺失。以后新架构支持该特性时需满足这条依赖 |
| 6 | `hugetlb_fault` mm/hugetlb.c:6130 | `set_huge_pte_at` | `ret = 0` | vma_end_read | 不是 | 同上 |
| 7 | `__irq_set_trigger` kernel/irq/manage.c:944 | `mask_irq` | `unmask = 1` | unmask_irq | 不是 | unmask = 1 记录“之后要恢复”，是状态记录 |
| 8 | `memtest` mm/memtest.c:48 | `__va` | `start_bad = 0` | reserve_bad_mem | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
| 9 | `do_swap_page` mm/memory.c:5042 | `pte_same` | `nr_pages = 1` | swap_cache_del_folio | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
| 10 | `handler_chain` kernel/events/uprobes.c:2562 | `handler` | `has_consumers = true` | down_read、filter_chain、unapply_uprobe | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
| 11 | `ring_buffer_read_page` kernel/trace/ring_buffer.c:7304 | `local_set` | `read = 0` | atomic_long_set、rb_init_data_page | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
| 12 | `move_ptes` mm/mremap.c:267 | `pte_none` | `nr_ptes = 1` | get_and_clear_ptes、mremap_folio_pte_batch、pte_clear | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
| 13 | `string_get_size` lib/string_helpers.c:98 | `do_div` | `j = 0` | snprintf | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
| 14 | `do_swap_page` mm/memory.c:5042 | `ptep_get` | `nr_pages = 1` | swap_cache_del_folio | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
| 15 | `mincore_pte_range` mm/mincore.c:185 | `ptep_get` | `step = 1` | __mincore_unmapped_range、mincore_swap、pte_is_marker | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
| 16 | `move_ptes` mm/mremap.c:267 | `ptep_get` | `nr_ptes = 1` | get_and_clear_ptes、mremap_folio_pte_batch、pte_clear | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
| 17 | `trace_pid_list_is_set` kernel/trace/pid_list.c:143 | `cpu_relax` | `ret = false` | do_read_seqcount_retry | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
| 18 | `_vm_unmap_aliases` mm/vmalloc.c:2998 | `max` | `flush = 1` | flush_tlb_kernel_range | 不是 | flush = 1 表示“要刷”，方向相反（触发而不是跳过） |
| 19 | `__ftrace_event_enable_disable` kernel/trace/trace_events.c:895 | `set_bit` | `tgid = true` | tracing_stop_tgid_record | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
| 20 | `acpi_init_properties` drivers/acpi/property.c:603 | `strcmp` | `acpi_of = true` | acpi_handle_printk、acpi_init_of_compatible | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
| 21 | `audit_add_to_parent` kernel/audit_watch.c:378 | `strcmp` | `watch_found = 1` | audit_get_watch、list_add | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
| 22 | `enable_instances` kernel/trace/trace.c:9716 | `strcmp` | `traceoff = true` | tracer_tracing_off | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
| 23 | `audit_data_to_entry` kernel/auditfilter.c:536 | `pr_warn` | `err = 0` | kfree | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
| 24 | `cgroup_addrm_files` kernel/cgroup/cgroup.c:4575 | `pr_warn` | `is_add = false` | cgroup_rm_file | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
| 25 | `enable_instances` kernel/trace/trace.c:9744 | `pr_warn` | `memmap_area = true` | map_pages | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
| 26 | `bpf_core_calc_relo_insn` tools/lib/bpf/relo_core.c:1349 | `pr_warn` | `j = 0` | bpf_core_calc_relo、bpf_log | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
| 27 | `migrate_pages` mm/migrate.c:2114 | `memset` | `nr_pages = 0` | list_cut_before、list_splice_init | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
| 28 | `_vm_unmap_aliases` mm/vmalloc.c:2997 | `min` | `flush = 1` | flush_tlb_kernel_range | 不是 | 同上 |
| 29 | `print_instance` kernel/bpf/liveness.c:507 | `verbose` | `has_use = true` | bpf_vlog_reset | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
| 30 | `arg_track_log` kernel/bpf/liveness.c:1042 | `verbose` | `printed = true` | bpf_verbose_insn、bpf_verifier_log_write | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
| 31 | `propagate_precision` kernel/bpf/states.c:1038 | `verbose` | `first = false` | bpf_verifier_log_write | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
| 32 | `try_charge_memcg` mm/memcontrol.c:2710 | `get_current` | `raised_max_event = true` | __memcg_memory_event | 不是 | 普通控制流（返回码、计数、步长、状态记录），公共层没有因为相信接口的效果而跳过自己的工作 |
