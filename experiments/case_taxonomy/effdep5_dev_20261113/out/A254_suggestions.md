# 人工分析建议（纵向信号）：A254

接口 8858 个；纵向候选 30 个，其中有横向差异的 2 个（只用于排序，不是判错依据）。以下为前 50 条。

## 1. `kvm_get_dirty_log_protect` 调用 `kvm_arch_sync_dirty_log` 后跳过 `kvm_flush_remote_tlbs_memslot`（virt/kvm/kvm_main.c:2247）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`kvm、memslot` 在 `kvm_get_dirty_log_protect` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `kvm_arch_sync_dirty_log` 后把 `flush` 设为 `false`，不再自己保证
- 动态阶段可检查：后续使用 `kvm、memslot` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 2247 行调用 `kvm_arch_sync_dirty_log` 后，第 2250 行把 `flush` 设为 `false`；第 2285 行的 `kvm_flush_remote_tlbs_memslot`（mem 类效果）受 `flush` 控制；受它控制、有效果的调用共 1 个：`kvm_flush_remote_tlbs_memslot`
- 横向：`kvm_arch_sync_dirty_log` 平凡定义的架构 arm64、loongarch、mips、powerpc、riscv；非平凡的 s390、x86（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`kvm_arch_sync_dirty_log` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 3.7856

## 2. `kvm_clear_dirty_log_protect` 调用 `kvm_arch_sync_dirty_log` 后跳过 `kvm_flush_remote_tlbs_memslot`（virt/kvm/kvm_main.c:2369）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`kvm、memslot` 在 `kvm_clear_dirty_log_protect` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `kvm_arch_sync_dirty_log` 后把 `flush` 设为 `false`，不再自己保证
- 动态阶段可检查：后续使用 `kvm、memslot` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 2369 行调用 `kvm_arch_sync_dirty_log` 后，第 2371 行把 `flush` 设为 `false`；第 2402 行的 `kvm_flush_remote_tlbs_memslot`（mem 类效果）受 `flush` 控制；受它控制、有效果的调用共 1 个：`kvm_flush_remote_tlbs_memslot`
- 横向：`kvm_arch_sync_dirty_log` 平凡定义的架构 arm64、loongarch、mips、powerpc、riscv；非平凡的 s390、x86（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`kvm_arch_sync_dirty_log` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 3.7856

## 3. `acpi_os_read_memory` 调用 `acpi_os_ioremap` 后跳过 `rcu_read_unlock`（drivers/acpi/osl.c:758）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`（资源未识别）` 在 `acpi_os_read_memory` 之后被使用或发布之前，必须写入已排序、已写入（清零或初始化）；公共层在调用 `acpi_os_ioremap` 后把 `unmap` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `该资源` 时，它是否写入已排序、已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 758 行调用 `acpi_os_ioremap` 后，第 761 行把 `unmap` 设为 `true`；第 773 行的 `rcu_read_unlock`（barrier+mem 类效果）受 `unmap` 控制；受它控制、有效果的调用共 1 个：`rcu_read_unlock`
- 横向：`acpi_os_ioremap` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`acpi_os_ioremap` 是否产生了“写入已排序、已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 2.25

## 4. `acpi_os_write_memory` 调用 `acpi_os_ioremap` 后跳过 `rcu_read_unlock`（drivers/acpi/osl.c:789）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`（资源未识别）` 在 `acpi_os_write_memory` 之后被使用或发布之前，必须写入已排序、已写入（清零或初始化）；公共层在调用 `acpi_os_ioremap` 后把 `unmap` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `该资源` 时，它是否写入已排序、已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 789 行调用 `acpi_os_ioremap` 后，第 792 行把 `unmap` 设为 `true`；第 815 行的 `rcu_read_unlock`（barrier+mem 类效果）受 `unmap` 控制；受它控制、有效果的调用共 1 个：`rcu_read_unlock`
- 横向：`acpi_os_ioremap` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`acpi_os_ioremap` 是否产生了“写入已排序、已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 2.25

## 5. `__irq_set_trigger` 调用 `mask_irq` 后跳过 `unmask_irq`（kernel/irq/manage.c:943）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`desc` 在 `__irq_set_trigger` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `mask_irq` 后把 `unmask` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `desc` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 943 行调用 `mask_irq` 后，第 945 行把 `unmask` 设为 `1`；第 976 行的 `unmask_irq`（mem 类效果）受 `unmask` 控制；受它控制、有效果的调用共 1 个：`unmask_irq`
- 横向：`mask_irq` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`mask_irq` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.9464

## 6. `do_swap_page` 调用 `pte_same` 后跳过 `swap_cache_del_folio`（mm/memory.c:4917）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`folio` 在 `do_swap_page` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `pte_same` 后把 `nr_pages` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `folio` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 4917 行调用 `pte_same` 后，第 4925 行把 `nr_pages` 设为 `1`；第 4983 行的 `swap_cache_del_folio`（mem 类效果）受 `nr_pages` 控制；受它控制、有效果的调用共 2 个：`folio_free_swap`、`swap_cache_del_folio`
- 横向：`pte_same` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`pte_same` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.9

## 7. `memtest` 调用 `__va` 后跳过 `reserve_bad_mem`（mm/memtest.c:48）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`last_bad、pattern` 在 `memtest` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `__va` 后把 `start_bad` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `last_bad、pattern` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 48 行调用 `__va` 后，第 50 行把 `start_bad` 设为 `0`；第 66 行的 `reserve_bad_mem`（mem 类效果）受 `start_bad` 控制；受它控制、有效果的调用共 1 个：`reserve_bad_mem`
- 横向：`__va` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`__va` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.8672

## 8. `handler_chain` 调用 `handler` 后跳过 `down_read`（kernel/events/uprobes.c:2564）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`uprobe` 在 `handler_chain` 之后被使用或发布之前，必须已写入（清零或初始化）、已登记；公共层在调用 `handler` 后把 `has_consumers` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `uprobe` 时，它是否已写入（清零或初始化）、已登记（各架构分别检查性质，不比较架构间差异）
- 依据：第 2564 行调用 `handler` 后，第 2570 行把 `has_consumers` 设为 `true`；第 2587 行的 `down_read`（mem+register 类效果）受 `has_consumers` 控制；受它控制、有效果的调用共 4 个：`down_read`、`filter_chain`、`unapply_uprobe`、`up_read`
- 横向：`handler` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`handler` 是否产生了“已写入（清零或初始化）、已登记”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.7879

## 9. `ring_buffer_read_page` 调用 `local_set` 后跳过 `rb_init_data_page`（kernel/trace/ring_buffer.c:7186）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`dpage、reader` 在 `ring_buffer_read_page` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `local_set` 后把 `read` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `dpage、reader` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 7186 行调用 `local_set` 后，第 7190 行把 `read` 设为 `0`；第 7197 行的 `rb_init_data_page`（mem 类效果）受 `read` 控制；受它控制、有效果的调用共 2 个：`atomic_long_set`、`rb_init_data_page`
- 横向：`local_set` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`local_set` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.5803

## 10. `move_ptes` 调用 `pte_none` 后跳过 `mremap_folio_pte_batch`（mm/mremap.c:267）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`max_nr_ptes、mm、new_addr、new_ptep、old_addr、old_pte、old_ptep、pte、vma` 在 `move_ptes` 之后被使用或发布之前，必须已写入（清零或初始化）、页表项已设置；公共层在调用 `pte_none` 后把 `nr_ptes` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `max_nr_ptes、mm、new_addr、new_ptep、old_addr、old_pte、old_ptep、pte、vma` 时，它是否已写入（清零或初始化）、页表项已设置（各架构分别检查性质，不比较架构间差异）
- 依据：第 267 行调用 `pte_none` 后，第 269 行把 `nr_ptes` 设为 `1`；第 287 行的 `mremap_folio_pte_batch`（mem+pgtable 类效果）受 `nr_ptes` 控制；受它控制、有效果的调用共 7 个：`get_and_clear_ptes`、`mremap_folio_pte_batch`、`pte_clear`、`pte_clear_uffd_wp`、`pte_is_uffd_wp_marker`、`pte_swp_clear_uffd_wp`
- 横向：`pte_none` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`pte_none` 是否产生了“已写入（清零或初始化）、页表项已设置”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.5637

## 11. `string_get_size` 调用 `do_div` 后跳过 `snprintf`（lib/string_helpers.c:98）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`remainder、tmp` 在 `string_get_size` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `do_div` 后把 `j` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `remainder、tmp` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 98 行调用 `do_div` 后，第 105 行把 `j` 设为 `0`；第 125 行的 `snprintf`（mem 类效果）受 `j` 控制；受它控制、有效果的调用共 1 个：`snprintf`
- 横向：`do_div` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`do_div` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.4878

## 12. `do_swap_page` 调用 `ptep_get` 后跳过 `swap_cache_del_folio`（mm/memory.c:4917）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`folio` 在 `do_swap_page` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `ptep_get` 后把 `nr_pages` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `folio` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 4917 行调用 `ptep_get` 后，第 4925 行把 `nr_pages` 设为 `1`；第 4983 行的 `swap_cache_del_folio`（mem 类效果）受 `nr_pages` 控制；受它控制、有效果的调用共 2 个：`folio_free_swap`、`swap_cache_del_folio`
- 横向：`ptep_get` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`ptep_get` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.4668

## 13. `mincore_pte_range` 调用 `ptep_get` 后跳过 `pte_is_marker`（mm/mincore.c:186）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`addr、entry、pte、vec、vma` 在 `mincore_pte_range` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `ptep_get` 后把 `step` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `addr、entry、pte、vec、vma` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 186 行调用 `ptep_get` 后，第 188 行把 `step` 设为 `1`；第 190 行的 `pte_is_marker`（mem 类效果）受 `step` 控制；受它控制、有效果的调用共 4 个：`__mincore_unmapped_range`、`mincore_swap`、`pte_is_marker`、`softleaf_from_pte`
- 横向：`ptep_get` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`ptep_get` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.4668

## 14. `trace_pid_list_is_set` 调用 `cpu_relax` 后跳过 `do_read_seqcount_retry`（kernel/trace/pid_list.c:143）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`pid_list、seq` 在 `trace_pid_list_is_set` 之后被使用或发布之前，必须写入已排序；公共层在调用 `cpu_relax` 后把 `ret` 设为 `false`，不再自己保证
- 动态阶段可检查：后续使用 `pid_list、seq` 时，它是否写入已排序（各架构分别检查性质，不比较架构间差异）
- 依据：第 143 行调用 `cpu_relax` 后，第 144 行把 `ret` 设为 `false`；第 151 行的 `do_read_seqcount_retry`（barrier 类效果）受 `ret` 控制；受它控制、有效果的调用共 1 个：`do_read_seqcount_retry`
- 横向：`cpu_relax` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`cpu_relax` 是否产生了“写入已排序”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.4399

## 15. `_vm_unmap_aliases` 调用 `max` 后跳过 `flush_tlb_kernel_range`（mm/vmalloc.c:2976）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`end、start` 在 `_vm_unmap_aliases` 之后被使用或发布之前，必须TLB 已刷新；公共层在调用 `max` 后把 `flush` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `end、start` 时，它是否TLB 已刷新（各架构分别检查性质，不比较架构间差异）
- 依据：第 2976 行调用 `max` 后，第 2982 行把 `flush` 设为 `1`；第 2991 行的 `flush_tlb_kernel_range`（tlb 类效果）受 `flush` 控制；受它控制、有效果的调用共 1 个：`flush_tlb_kernel_range`
- 横向：`max` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`max` 是否产生了“TLB 已刷新”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3921

## 16. `__ftrace_event_enable_disable` 调用 `set_bit` 后跳过 `tracing_stop_tgid_record`（kernel/trace/trace_events.c:868）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`（资源未识别）` 在 `__ftrace_event_enable_disable` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `set_bit` 后把 `tgid` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `该资源` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 868 行调用 `set_bit` 后，第 872 行把 `tgid` 设为 `true`；第 882 行的 `tracing_stop_tgid_record`（mem 类效果）受 `tgid` 控制；受它控制、有效果的调用共 1 个：`tracing_stop_tgid_record`
- 横向：`set_bit` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`set_bit` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3791

## 17. `audit_data_to_entry` 调用 `pr_warn` 后跳过 `kfree`（kernel/auditfilter.c:536）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`str` 在 `audit_data_to_entry` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `pr_warn` 后把 `err` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `str` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 536 行调用 `pr_warn` 后，第 538 行把 `err` 设为 `0`；第 550 行的 `kfree`（mem 类效果）受 `err` 控制；受它控制、有效果的调用共 1 个：`kfree`
- 横向：`pr_warn` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`pr_warn` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3512

## 18. `cgroup_addrm_files` 调用 `pr_warn` 后跳过 `cgroup_rm_file`（kernel/cgroup/cgroup.c:4479）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`cft、cgrp` 在 `cgroup_addrm_files` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `pr_warn` 后把 `is_add` 设为 `false`，不再自己保证
- 动态阶段可检查：后续使用 `cft、cgrp` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 4479 行调用 `pr_warn` 后，第 4482 行把 `is_add` 设为 `false`；第 4486 行的 `cgroup_rm_file`（mem 类效果）受 `is_add` 控制；受它控制、有效果的调用共 1 个：`cgroup_rm_file`
- 横向：`pr_warn` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`pr_warn` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3512

## 19. `enable_instances` 调用 `pr_warn` 后跳过 `map_pages`（kernel/trace/trace.c:9687）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`size、start` 在 `enable_instances` 之后被使用或发布之前，必须缓存已同步、已写入（清零或初始化）、TLB 已刷新；公共层在调用 `pr_warn` 后把 `memmap_area` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `size、start` 时，它是否缓存已同步、已写入（清零或初始化）、TLB 已刷新（各架构分别检查性质，不比较架构间差异）
- 依据：第 9687 行调用 `pr_warn` 后，第 9691 行把 `memmap_area` 设为 `true`；第 9713 行的 `map_pages`（cache+mem+tlb 类效果）受 `memmap_area` 控制；受它控制、有效果的调用共 1 个：`map_pages`
- 横向：`pr_warn` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`pr_warn` 是否产生了“缓存已同步、已写入（清零或初始化）、TLB 已刷新”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3512

## 20. `bpf_core_calc_relo_insn` 调用 `pr_warn` 后跳过 `bpf_log`（tools/lib/bpf/relo_core.c:1349）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`cand_res、cand_spec、local_spec、prog_name、relo、relo_idx、targ_res、targ_spec` 在 `bpf_core_calc_relo_insn` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `pr_warn` 后把 `j` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `cand_res、cand_spec、local_spec、prog_name、relo、relo_idx、targ_res、targ_spec` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 1349 行调用 `pr_warn` 后，第 1354 行把 `j` 设为 `0`；第 1382 行的 `bpf_log`（mem 类效果）受 `j` 控制；受它控制、有效果的调用共 2 个：`bpf_core_calc_relo`、`bpf_log`
- 横向：`pr_warn` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`pr_warn` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3512

## 21. `migrate_pages` 调用 `memset` 后跳过 `list_cut_before`（mm/migrate.c:2103）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`folio2、folios、from` 在 `migrate_pages` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `memset` 后把 `nr_pages` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `folio2、folios、from` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 2103 行调用 `memset` 后，第 2111 行把 `nr_pages` 设为 `0`；第 2124 行的 `list_cut_before`（mem 类效果）受 `nr_pages` 控制；受它控制、有效果的调用共 2 个：`list_cut_before`、`list_splice_init`
- 横向：`memset` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`memset` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3418

## 22. `acpi_init_properties` 调用 `strcmp` 后跳过 `acpi_init_of_compatible`（drivers/acpi/property.c:603）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`adev` 在 `acpi_init_properties` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `strcmp` 后把 `acpi_of` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `adev` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 603 行调用 `strcmp` 后，第 604 行把 `acpi_of` 设为 `true`；第 617 行的 `acpi_init_of_compatible`（mem 类效果）受 `acpi_of` 控制；受它控制、有效果的调用共 2 个：`acpi_handle_printk`、`acpi_init_of_compatible`
- 横向：`strcmp` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`strcmp` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3381

## 23. `audit_add_to_parent` 调用 `strcmp` 后跳过 `audit_get_watch`（kernel/audit_watch.c:378）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`parent、watch` 在 `audit_add_to_parent` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `strcmp` 后把 `watch_found` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `parent、watch` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 378 行调用 `strcmp` 后，第 381 行把 `watch_found` 设为 `1`；第 396 行的 `audit_get_watch`（mem 类效果）受 `watch_found` 控制；受它控制、有效果的调用共 2 个：`audit_get_watch`、`list_add`
- 横向：`strcmp` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`strcmp` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3381

## 24. `enable_instances` 调用 `strcmp` 后跳过 `tracer_tracing_off`（kernel/trace/trace.c:9659）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`tr` 在 `enable_instances` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `strcmp` 后把 `traceoff` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `tr` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 9659 行调用 `strcmp` 后，第 9660 行把 `traceoff` 设为 `true`；第 9735 行的 `tracer_tracing_off`（mem 类效果）受 `traceoff` 控制；受它控制、有效果的调用共 1 个：`tracer_tracing_off`
- 横向：`strcmp` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`strcmp` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3381

## 25. `_vm_unmap_aliases` 调用 `min` 后跳过 `flush_tlb_kernel_range`（mm/vmalloc.c:2975）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`end、start` 在 `_vm_unmap_aliases` 之后被使用或发布之前，必须TLB 已刷新；公共层在调用 `min` 后把 `flush` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `end、start` 时，它是否TLB 已刷新（各架构分别检查性质，不比较架构间差异）
- 依据：第 2975 行调用 `min` 后，第 2982 行把 `flush` 设为 `1`；第 2991 行的 `flush_tlb_kernel_range`（tlb 类效果）受 `flush` 控制；受它控制、有效果的调用共 1 个：`flush_tlb_kernel_range`
- 横向：`min` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`min` 是否产生了“TLB 已刷新”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3305

## 26. `print_instance` 调用 `verbose` 后跳过 `bpf_vlog_reset`（kernel/bpf/liveness.c:509）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`env、has_use、pos` 在 `print_instance` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `verbose` 后把 `has_use` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `env、has_use、pos` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 509 行调用 `verbose` 后，第 510 行把 `has_use` 设为 `true`；第 513 行的 `bpf_vlog_reset`（mem 类效果）受 `has_use` 控制；受它控制、有效果的调用共 1 个：`bpf_vlog_reset`
- 横向：`verbose` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`verbose` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3199

## 27. `arg_track_log` 调用 `verbose` 后跳过 `bpf_verifier_log_write`（kernel/bpf/liveness.c:1044）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`env、idx、insn` 在 `arg_track_log` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `verbose` 后把 `printed` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `env、idx、insn` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 1044 行调用 `verbose` 后，第 1047 行把 `printed` 设为 `true`；第 1059 行的 `bpf_verifier_log_write`（mem 类效果）受 `printed` 控制；受它控制、有效果的调用共 3 个：`bpf_verbose_insn`、`bpf_verifier_log_write`、`bpf_vlog_reset`
- 横向：`verbose` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`verbose` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3199

## 28. `propagate_precision` 调用 `verbose` 后跳过 `bpf_verifier_log_write`（kernel/bpf/states.c:1039）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`env、fr、i` 在 `propagate_precision` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `verbose` 后把 `first` 设为 `false`，不再自己保证
- 动态阶段可检查：后续使用 `env、fr、i` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 1039 行调用 `verbose` 后，第 1044 行把 `first` 设为 `false`；第 1056 行的 `bpf_verifier_log_write`（mem 类效果）受 `first` 控制；受它控制、有效果的调用共 1 个：`bpf_verifier_log_write`
- 横向：`verbose` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`verbose` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3199

## 29. `check_stack_read_fixed_off` 调用 `verbose` 后跳过 `bpf_push_jmp_history`（kernel/bpf/verifier.c:3877）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`env、hist_frame、hist_spi` 在 `check_stack_read_fixed_off` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `verbose` 后把 `insn_flags` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `env、hist_frame、hist_spi` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 3877 行调用 `verbose` 后，第 3884 行把 `insn_flags` 设为 `0`；第 3887 行的 `bpf_push_jmp_history`（mem 类效果）受 `insn_flags` 控制；受它控制、有效果的调用共 1 个：`bpf_push_jmp_history`
- 横向：`verbose` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`verbose` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3199

## 30. `try_charge_memcg` 调用 `get_current` 后跳过 `__memcg_memory_event`（mm/memcontrol.c:2645）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`allow_spinning、mem_over_limit` 在 `try_charge_memcg` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `get_current` 后把 `raised_max_event` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `allow_spinning、mem_over_limit` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 2645 行调用 `get_current` 后，第 2652 行把 `raised_max_event` 设为 `true`；第 2718 行的 `__memcg_memory_event`（mem 类效果）受 `raised_max_event` 控制；受它控制、有效果的调用共 1 个：`__memcg_memory_event`
- 横向：`get_current` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`get_current` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.2333

