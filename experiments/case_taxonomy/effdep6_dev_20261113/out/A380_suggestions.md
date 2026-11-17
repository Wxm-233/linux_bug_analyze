# 人工分析建议（纵向信号 + 效果对上效果）：A380

接口 8860 个；纵向候选 8 个，其中有横向差异的 1 个（只用于排序，不是判错依据）。以下为前 50 条。

## 1. `acpi_os_read_memory` 调用 `acpi_os_ioremap` 后跳过 `rcu_read_unlock`（drivers/acpi/osl.c:752）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`（资源未识别）` 在 `acpi_os_read_memory` 之后被使用或发布之前，必须写入已排序、已写入（清零或初始化）；公共层在调用 `acpi_os_ioremap` 后把 `unmap` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `该资源` 时，它是否写入已排序、已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 752 行调用 `acpi_os_ioremap` 后，第 755 行把 `unmap` 设为 `true`；第 767 行的 `rcu_read_unlock`（barrier+mem 类效果）受 `unmap` 控制；受它控制、有效果的调用共 1 个：`rcu_read_unlock`
- 效果对上效果：被跳过的工作属于 barrier+mem 类；`acpi_os_ioremap` 的实现有 mem 类（按架构：仅 riscv 事实）；重合 mem
- 横向：`acpi_os_ioremap` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`acpi_os_ioremap` 是否产生了“写入已排序、已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 2.25

## 2. `acpi_os_write_memory` 调用 `acpi_os_ioremap` 后跳过 `rcu_read_unlock`（drivers/acpi/osl.c:783）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`（资源未识别）` 在 `acpi_os_write_memory` 之后被使用或发布之前，必须写入已排序、已写入（清零或初始化）；公共层在调用 `acpi_os_ioremap` 后把 `unmap` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `该资源` 时，它是否写入已排序、已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 783 行调用 `acpi_os_ioremap` 后，第 786 行把 `unmap` 设为 `true`；第 809 行的 `rcu_read_unlock`（barrier+mem 类效果）受 `unmap` 控制；受它控制、有效果的调用共 1 个：`rcu_read_unlock`
- 效果对上效果：被跳过的工作属于 barrier+mem 类；`acpi_os_ioremap` 的实现有 mem 类（按架构：仅 riscv 事实）；重合 mem
- 横向：`acpi_os_ioremap` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`acpi_os_ioremap` 是否产生了“写入已排序、已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 2.25

## 3. `__irq_set_trigger` 调用 `mask_irq` 后跳过 `unmask_irq`（kernel/irq/manage.c:943）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`desc` 在 `__irq_set_trigger` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `mask_irq` 后把 `unmask` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `desc` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 943 行调用 `mask_irq` 后，第 945 行把 `unmask` 设为 `1`；第 976 行的 `unmask_irq`（mem 类效果）受 `unmask` 控制；受它控制、有效果的调用共 1 个：`unmask_irq`
- 效果对上效果：被跳过的工作属于 mem 类；`mask_irq` 的实现有 mem 类（按架构：仅 riscv 事实）；重合 mem
- 横向：`mask_irq` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`mask_irq` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.9464

## 4. `trace_pid_list_is_set` 调用 `cpu_relax` 后跳过 `do_read_seqcount_retry`（kernel/trace/pid_list.c:143）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`pid_list、seq` 在 `trace_pid_list_is_set` 之后被使用或发布之前，必须写入已排序；公共层在调用 `cpu_relax` 后把 `ret` 设为 `false`，不再自己保证
- 动态阶段可检查：后续使用 `pid_list、seq` 时，它是否写入已排序（各架构分别检查性质，不比较架构间差异）
- 依据：第 143 行调用 `cpu_relax` 后，第 144 行把 `ret` 设为 `false`；第 151 行的 `do_read_seqcount_retry`（barrier 类效果）受 `ret` 控制；受它控制、有效果的调用共 1 个：`do_read_seqcount_retry`
- 效果对上效果：被跳过的工作属于 barrier 类；`cpu_relax` 的实现有 barrier 类（按架构：arm barrier；mips barrier）；重合 barrier
- 横向：`cpu_relax` 平凡定义的架构 um；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`cpu_relax` 是否产生了“写入已排序”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.8797

## 5. `ring_buffer_read_page` 调用 `local_set` 后跳过 `rb_init_page`（kernel/trace/ring_buffer.c:6736）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`bpage、reader` 在 `ring_buffer_read_page` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `local_set` 后把 `read` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `bpage、reader` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 6736 行调用 `local_set` 后，第 6740 行把 `read` 设为 `0`；第 6747 行的 `rb_init_page`（mem 类效果）受 `read` 控制；受它控制、有效果的调用共 2 个：`atomic_long_set`、`rb_init_page`
- 效果对上效果：被跳过的工作属于 mem 类；`local_set` 的实现有 mem 类（按架构：alpha mem；loongarch mem；mips mem；x86 mem）；重合 mem
- 横向：`local_set` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`local_set` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.5947

## 6. `move_ptes` 调用 `pte_none` 后跳过 `mremap_folio_pte_batch`（mm/mremap.c:267）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`max_nr_ptes、mm、new_addr、new_ptep、old_addr、old_pte、old_ptep、pte、vma` 在 `move_ptes` 之后被使用或发布之前，必须已写入（清零或初始化）、页表项已设置；公共层在调用 `pte_none` 后把 `nr_ptes` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `max_nr_ptes、mm、new_addr、new_ptep、old_addr、old_pte、old_ptep、pte、vma` 时，它是否已写入（清零或初始化）、页表项已设置（各架构分别检查性质，不比较架构间差异）
- 依据：第 267 行调用 `pte_none` 后，第 269 行把 `nr_ptes` 设为 `1`；第 287 行的 `mremap_folio_pte_batch`（mem+pgtable 类效果）受 `nr_ptes` 控制；受它控制、有效果的调用共 7 个：`get_and_clear_ptes`、`mremap_folio_pte_batch`、`pte_clear`、`pte_clear_uffd_wp`、`pte_is_uffd_wp_marker`、`pte_swp_clear_uffd_wp`
- 效果对上效果：被跳过的工作属于 barrier+cache+mem+pgtable 类；`pte_none` 的实现有 mem 类（按架构：um mem）；重合 mem
- 横向：`pte_none` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`pte_none` 是否产生了“已写入（清零或初始化）、页表项已设置”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.5637

## 7. `migrate_pages` 调用 `memset` 后跳过 `list_cut_before`（mm/migrate.c:2086）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`folio2、folios、from` 在 `migrate_pages` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `memset` 后把 `nr_pages` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `folio2、folios、from` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 2086 行调用 `memset` 后，第 2094 行把 `nr_pages` 设为 `0`；第 2107 行的 `list_cut_before`（mem 类效果）受 `nr_pages` 控制；受它控制、有效果的调用共 2 个：`list_cut_before`、`list_splice_init`
- 效果对上效果：被跳过的工作属于 mem 类；`memset` 的实现有 mem 类（按架构：arm mem；arm64 mem；loongarch mem；powerpc mem）；重合 mem
- 横向：`memset` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`memset` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3428

## 8. `check_stack_read_fixed_off` 调用 `verbose` 后跳过 `push_jmp_history`（kernel/bpf/verifier.c:5656）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`env` 在 `check_stack_read_fixed_off` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `verbose` 后把 `insn_flags` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `env` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 5656 行调用 `verbose` 后，第 5662 行把 `insn_flags` 设为 `0`；第 5665 行的 `push_jmp_history`（mem 类效果）受 `insn_flags` 控制；受它控制、有效果的调用共 1 个：`push_jmp_history`
- 效果对上效果：被跳过的工作属于 mem 类；`verbose` 的实现有 mem 类（按架构：仅 riscv 事实）；重合 mem
- 横向：`verbose` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`verbose` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.324

