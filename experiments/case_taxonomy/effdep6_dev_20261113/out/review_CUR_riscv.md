# 当前版本 riscv：效果对上效果之后的候选人工核对

过滤前 32 个候选，过滤后剩 11 个，全部核对。判断标准同 effdep5 修订 1 第 3 条。核对人 Claude。

结果：不是 10，真实依赖，当前满足 1。

| # | 位置 | 接口 | 标志 | 被跳过的调用 | 重合类别 | 判断 | 理由 |
|---|---|---|---|---|---|---|---|
| 1 | `acpi_os_read_memory` drivers/acpi/osl.c:758 | `acpi_os_ioremap` | `unmap = true` | rcu_read_unlock | mem | 不是 | unmap = true 记录映射来源，之后对称释放；被跳过的 rcu_read_unlock 是另一条分支的解锁，与 ioremap 的效果无关 |
| 2 | `acpi_os_write_memory` drivers/acpi/osl.c:789 | `acpi_os_ioremap` | `unmap = true` | rcu_read_unlock | mem | 不是 | unmap = true 记录映射来源，之后对称释放；被跳过的 rcu_read_unlock 是另一条分支的解锁，与 ioremap 的效果无关 |
| 3 | `do_swap_page` mm/memory.c:5175 | `pte_modify` | `rwp_restore = true` | do_wp_page | mem+pgtable | 真实依赖，当前满足 | 跳过写时复制依赖 pte_modify 保留 _PAGE_UFFD；x86 显式、arm64 和 riscv 用掩码保留，三个支持 USERFAULTFD_RWP 的架构都满足（详见 effdep5 核对） |
| 4 | `__irq_set_trigger` kernel/irq/manage.c:944 | `mask_irq` | `unmask = 1` | unmask_irq | mem | 不是 | unmask = 1 记录“之后要恢复”，状态记录 |
| 5 | `ring_buffer_read_page` kernel/trace/ring_buffer.c:7304 | `local_set` | `read = 0` | atomic_long_set、rb_init_data_page | mem | 不是 | read = 0 是读取偏移量；跳过的是初始化数据页的另一条分支 |
| 6 | `move_ptes` mm/mremap.c:267 | `pte_none` | `nr_ptes = 1` | get_and_clear_ptes、mremap_folio_pte_batch、pte_clear | mem | 不是 | nr_ptes = 1 是批处理步长 |
| 7 | `trace_pid_list_is_set` kernel/trace/pid_list.c:143 | `cpu_relax` | `ret = false` | do_read_seqcount_retry | barrier | 不是 | ret = false 是返回值，循环里重试读 seqcount |
| 8 | `migrate_pages` mm/migrate.c:2114 | `memset` | `nr_pages = 0` | list_cut_before、list_splice_init | mem | 不是 | nr_pages = 0 是计数 |
| 9 | `print_instance` kernel/bpf/liveness.c:507 | `verbose` | `has_use = true` | bpf_vlog_reset | mem | 不是 | 日志打印的开关（has_use、printed、first），与 verbose 的效果无关 |
| 10 | `arg_track_log` kernel/bpf/liveness.c:1042 | `verbose` | `printed = true` | bpf_verbose_insn、bpf_verifier_log_write | mem | 不是 | 日志打印的开关（has_use、printed、first），与 verbose 的效果无关 |
| 11 | `propagate_precision` kernel/bpf/states.c:1038 | `verbose` | `first = false` | bpf_verifier_log_write | mem | 不是 | 日志打印的开关（has_use、printed、first），与 verbose 的效果无关 |
