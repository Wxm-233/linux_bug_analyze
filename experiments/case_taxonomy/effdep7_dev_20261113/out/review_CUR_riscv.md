# 当前版本 riscv：加“同一资源”条件后的候选人工核对

effdep6 过滤后 11 个，本轮剩 6 个，全部核对：不是 6。判断标准同 effdep5 修订 1 第 3 条。核对人 Claude。

effdep5、effdep6 找到的那条真实依赖（`do_swap_page`、`pte_modify`）按事先预期被去掉：`pte_modify(pte, ...)` 和 `do_wp_page(vmf)` 不共享实参基变量。

| # | 位置 | 接口 | 标志 | 共享资源的被跳过调用 | 共享资源 | 判断 | 理由 |
|---|---|---|---|---|---|---|---|
| 1 | `__irq_set_trigger` kernel/irq/manage.c:944 | `mask_irq` | `unmask = 1` | unmask_irq | desc | 不是 | 共享的 desc 是中断描述符这个上下文对象；unmask = 1 记录“之后要恢复”，不是相信 mask_irq 替它做了 unmask_irq 的事 |
| 2 | `ring_buffer_read_page` kernel/trace/ring_buffer.c:7304 | `local_set` | `read = 0` | atomic_long_set、rb_init_data_page | dpage | 不是 | 共享的 dpage 是数据页；read = 0 是读取偏移量，被跳过的初始化在另一条分支，与 local_set 无关 |
| 3 | `move_ptes` mm/mremap.c:267 | `pte_none` | `nr_ptes = 1` | pte_clear、set_ptes | new_ptep | 不是 | 共享的 new_ptep；nr_ptes = 1 是批处理步长，pte_none 只是判断，没有效果 |
| 4 | `print_instance` kernel/bpf/liveness.c:507 | `verbose` | `has_use = true` | bpf_vlog_reset | env | 不是 | 共享的 env 是验证器的上下文对象，几乎每个调用都传它；标志是日志打印开关 |
| 5 | `arg_track_log` kernel/bpf/liveness.c:1042 | `verbose` | `printed = true` | bpf_verbose_insn、bpf_verifier_log_write | env、idx | 不是 | 共享的 env 是验证器的上下文对象，几乎每个调用都传它；标志是日志打印开关 |
| 6 | `propagate_precision` kernel/bpf/states.c:1038 | `verbose` | `first = false` | bpf_verifier_log_write | env、fr、i | 不是 | 共享的 env 是验证器的上下文对象，几乎每个调用都传它；标志是日志打印开关 |
