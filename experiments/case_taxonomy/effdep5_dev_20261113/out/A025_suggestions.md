# 人工分析建议（纵向信号）：A025

接口 8286 个；纵向候选 24 个，其中有横向差异的 1 个（只用于排序，不是判错依据）。以下为前 50 条。

## 1. `post_alloc_hook` 调用 `tag_clear_highpage` 后跳过 `kasan_has_integrated_init`（mm/page_alloc.c:1515）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`order、page` 在 `post_alloc_hook` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `tag_clear_highpage` 后把 `init` 设为 `false`，不再自己保证
- 动态阶段可检查：后续使用 `order、page` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 1515 行调用 `tag_clear_highpage` 后，第 1518 行把 `init` 设为 `false`；第 1523 行的 `kasan_has_integrated_init`（mem 类效果）受 `init` 控制；受它控制、有效果的调用共 2 个：`kasan_has_integrated_init`、`kernel_init_pages`
- 横向：`tag_clear_highpage` 平凡定义的架构 alpha、arc、arm、csky、hexagon、loongarch、m68k、microblaze；非平凡的 arm64（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`tag_clear_highpage` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 6.0

## 2. `acpi_os_read_memory` 调用 `acpi_os_ioremap` 后跳过 `rcu_read_unlock`（drivers/acpi/osl.c:723）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`（资源未识别）` 在 `acpi_os_read_memory` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `acpi_os_ioremap` 后把 `unmap` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `该资源` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 723 行调用 `acpi_os_ioremap` 后，第 726 行把 `unmap` 设为 `true`；第 738 行的 `rcu_read_unlock`（mem 类效果）受 `unmap` 控制；受它控制、有效果的调用共 1 个：`rcu_read_unlock`
- 横向：`acpi_os_ioremap` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`acpi_os_ioremap` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 2.25

## 3. `acpi_os_write_memory` 调用 `acpi_os_ioremap` 后跳过 `rcu_read_unlock`（drivers/acpi/osl.c:754）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`（资源未识别）` 在 `acpi_os_write_memory` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `acpi_os_ioremap` 后把 `unmap` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `该资源` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 754 行调用 `acpi_os_ioremap` 后，第 757 行把 `unmap` 设为 `true`；第 780 行的 `rcu_read_unlock`（mem 类效果）受 `unmap` 控制；受它控制、有效果的调用共 1 个：`rcu_read_unlock`
- 横向：`acpi_os_ioremap` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`acpi_os_ioremap` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 2.25

## 4. `__irq_set_trigger` 调用 `mask_irq` 后跳过 `unmask_irq`（kernel/irq/manage.c:972）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`desc` 在 `__irq_set_trigger` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `mask_irq` 后把 `unmask` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `desc` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 972 行调用 `mask_irq` 后，第 974 行把 `unmask` 设为 `1`；第 1005 行的 `unmask_irq`（mem 类效果）受 `unmask` 控制；受它控制、有效果的调用共 1 个：`unmask_irq`
- 横向：`mask_irq` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`mask_irq` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.9464

## 5. `memtest` 调用 `__va` 后跳过 `reserve_bad_mem`（mm/memtest.c:48）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`last_bad、pattern` 在 `memtest` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `__va` 后把 `start_bad` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `last_bad、pattern` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 48 行调用 `__va` 后，第 50 行把 `start_bad` 设为 `0`；第 64 行的 `reserve_bad_mem`（mem 类效果）受 `start_bad` 控制；受它控制、有效果的调用共 1 个：`reserve_bad_mem`
- 横向：`__va` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`__va` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.9464

## 6. `setup_sgl_buf` 调用 `virt_to_page` 后跳过 `sg_set_page`（lib/kfifo.c:310）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`off、page、sgl` 在 `setup_sgl_buf` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `virt_to_page` 后把 `l` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `off、page、sgl` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 310 行调用 `virt_to_page` 后，第 312 行把 `l` 设为 `0`；第 321 行的 `sg_set_page`（mem 类效果）受 `l` 控制；受它控制、有效果的调用共 1 个：`sg_set_page`
- 横向：`virt_to_page` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`virt_to_page` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.5529

## 7. `string_get_size` 调用 `do_div` 后跳过 `snprintf`（lib/string_helpers.c:94）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`remainder、tmp` 在 `string_get_size` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `do_div` 后把 `j` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `remainder、tmp` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 94 行调用 `do_div` 后，第 101 行把 `j` 设为 `0`；第 121 行的 `snprintf`（mem 类效果）受 `j` 控制；受它控制、有效果的调用共 1 个：`snprintf`
- 横向：`do_div` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`do_div` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.5058

## 8. `_vm_unmap_aliases` 调用 `max` 后跳过 `flush_tlb_kernel_range`（mm/vmalloc.c:2292）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`end、start` 在 `_vm_unmap_aliases` 之后被使用或发布之前，必须TLB 已刷新；公共层在调用 `max` 后把 `flush` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `end、start` 时，它是否TLB 已刷新（各架构分别检查性质，不比较架构间差异）
- 依据：第 2292 行调用 `max` 后，第 2298 行把 `flush` 设为 `1`；第 2307 行的 `flush_tlb_kernel_range`（tlb 类效果）受 `flush` 控制；受它控制、有效果的调用共 1 个：`flush_tlb_kernel_range`
- 横向：`max` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`max` 是否产生了“TLB 已刷新”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.4113

## 9. `audit_data_to_entry` 调用 `pr_warn` 后跳过 `kfree`（kernel/auditfilter.c:536）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`str` 在 `audit_data_to_entry` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `pr_warn` 后把 `err` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `str` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 536 行调用 `pr_warn` 后，第 538 行把 `err` 设为 `0`；第 550 行的 `kfree`（mem 类效果）受 `err` 控制；受它控制、有效果的调用共 1 个：`kfree`
- 横向：`pr_warn` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`pr_warn` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3772

## 10. `cgroup_addrm_files` 调用 `pr_warn` 后跳过 `cgroup_rm_file`（kernel/cgroup/cgroup.c:4273）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`cft、cgrp` 在 `cgroup_addrm_files` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `pr_warn` 后把 `is_add` 设为 `false`，不再自己保证
- 动态阶段可检查：后续使用 `cft、cgrp` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 4273 行调用 `pr_warn` 后，第 4276 行把 `is_add` 设为 `false`；第 4280 行的 `cgroup_rm_file`（mem 类效果）受 `is_add` 控制；受它控制、有效果的调用共 1 个：`cgroup_rm_file`
- 横向：`pr_warn` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`pr_warn` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3772

## 11. `bpf_core_calc_relo_insn` 调用 `pr_warn` 后跳过 `bpf_log`（tools/lib/bpf/relo_core.c:1332）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`cand_res、cand_spec、local_spec、prog_name、relo、relo_idx、targ_res、targ_spec` 在 `bpf_core_calc_relo_insn` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `pr_warn` 后把 `j` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `cand_res、cand_spec、local_spec、prog_name、relo、relo_idx、targ_res、targ_spec` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 1332 行调用 `pr_warn` 后，第 1337 行把 `j` 设为 `0`；第 1365 行的 `bpf_log`（mem 类效果）受 `j` 控制；受它控制、有效果的调用共 2 个：`bpf_core_calc_relo`、`bpf_log`
- 横向：`pr_warn` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`pr_warn` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3772

## 12. `_vm_unmap_aliases` 调用 `min` 后跳过 `flush_tlb_kernel_range`（mm/vmalloc.c:2291）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`end、start` 在 `_vm_unmap_aliases` 之后被使用或发布之前，必须TLB 已刷新；公共层在调用 `min` 后把 `flush` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `end、start` 时，它是否TLB 已刷新（各架构分别检查性质，不比较架构间差异）
- 依据：第 2291 行调用 `min` 后，第 2298 行把 `flush` 设为 `1`；第 2307 行的 `flush_tlb_kernel_range`（tlb 类效果）受 `flush` 控制；受它控制、有效果的调用共 1 个：`flush_tlb_kernel_range`
- 横向：`min` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`min` 是否产生了“TLB 已刷新”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3688

## 13. `free_unref_page_list` 调用 `__preempt_count_sub` 后跳过 `free_one_page`（mm/page_alloc.c:2563）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`migratetype、page、zone` 在 `free_unref_page_list` 之后被使用或发布之前，必须已写入（清零或初始化）、已登记；公共层在调用 `__preempt_count_sub` 后把 `batch_count` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `migratetype、page、zone` 时，它是否已写入（清零或初始化）、已登记（各架构分别检查性质，不比较架构间差异）
- 依据：第 2563 行调用 `__preempt_count_sub` 后，第 2567 行把 `batch_count` 设为 `0`；第 2577 行的 `free_one_page`（mem+register 类效果）受 `batch_count` 控制；受它控制、有效果的调用共 1 个：`free_one_page`
- 横向：`__preempt_count_sub` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`__preempt_count_sub` 是否产生了“已写入（清零或初始化）、已登记”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3644

## 14. `acpi_init_properties` 调用 `strcmp` 后跳过 `acpi_init_of_compatible`（drivers/acpi/property.c:552）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`adev` 在 `acpi_init_properties` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `strcmp` 后把 `acpi_of` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `adev` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 552 行调用 `strcmp` 后，第 553 行把 `acpi_of` 设为 `true`；第 566 行的 `acpi_init_of_compatible`（mem 类效果）受 `acpi_of` 控制；受它控制、有效果的调用共 2 个：`acpi_handle_printk`、`acpi_init_of_compatible`
- 横向：`strcmp` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`strcmp` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3588

## 15. `audit_add_to_parent` 调用 `strcmp` 后跳过 `audit_get_watch`（kernel/audit_watch.c:374）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`parent、watch` 在 `audit_add_to_parent` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `strcmp` 后把 `watch_found` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `parent、watch` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 374 行调用 `strcmp` 后，第 377 行把 `watch_found` 设为 `1`；第 392 行的 `audit_get_watch`（mem 类效果）受 `watch_found` 控制；受它控制、有效果的调用共 2 个：`audit_get_watch`、`list_add`
- 横向：`strcmp` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`strcmp` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3588

## 16. `migrate_pages` 调用 `memset` 后跳过 `list_cut_before`（mm/migrate.c:1918）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`folio2、folios、from` 在 `migrate_pages` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `memset` 后把 `nr_pages` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `folio2、folios、from` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 1918 行调用 `memset` 后，第 1926 行把 `nr_pages` 设为 `0`；第 1939 行的 `list_cut_before`（mem 类效果）受 `nr_pages` 控制；受它控制、有效果的调用共 2 个：`list_cut_before`、`list_splice_init`
- 横向：`memset` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`memset` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.351

## 17. `asn1_ber_decoder` 调用 `unlikely` 后跳过 `_printk`（lib/asn1_decoder.c:271）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`（资源未识别）` 在 `asn1_ber_decoder` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `unlikely` 后把 `len` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `该资源` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 271 行调用 `unlikely` 后，第 276 行把 `len` 设为 `0`；第 424 行的 `_printk`（mem 类效果）受 `len` 控制；受它控制、有效果的调用共 1 个：`_printk`
- 横向：`unlikely` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`unlikely` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.2842

## 18. `filemap_fault` 调用 `unlikely` 后跳过 `folio_put`（mm/filemap.c:3224）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`folio、mapping` 在 `filemap_fault` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `unlikely` 后把 `mapping_locked` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `folio、mapping` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 3224 行调用 `unlikely` 后，第 3226 行把 `mapping_locked` 设为 `true`；第 3279 行的 `folio_put`（mem 类效果）受 `mapping_locked` 控制；受它控制、有效果的调用共 2 个：`filemap_invalidate_unlock_shared`、`folio_put`
- 横向：`unlikely` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`unlikely` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.2842

## 19. `hugetlb_no_page` 调用 `unlikely` 后跳过 `hugepage_add_new_anon_rmap`（mm/hugetlb.c:6218）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`folio、haddr、vma` 在 `hugetlb_no_page` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `unlikely` 后把 `anon_rmap` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `folio、haddr、vma` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 6218 行调用 `unlikely` 后，第 6222 行把 `anon_rmap` 设为 `1`；第 6273 行的 `hugepage_add_new_anon_rmap`（mem 类效果）受 `anon_rmap` 控制；受它控制、有效果的调用共 1 个：`hugepage_add_new_anon_rmap`
- 横向：`unlikely` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`unlikely` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.2842

## 20. `try_charge_memcg` 调用 `unlikely` 后跳过 `memcg_memory_event`（mm/memcontrol.c:2732）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`mem_over_limit` 在 `try_charge_memcg` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `unlikely` 后把 `raised_max_event` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `mem_over_limit` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 2732 行调用 `unlikely` 后，第 2739 行把 `raised_max_event` 设为 `true`；第 2811 行的 `memcg_memory_event`（mem 类效果）受 `raised_max_event` 控制；受它控制、有效果的调用共 1 个：`memcg_memory_event`
- 横向：`unlikely` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`unlikely` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.2842

## 21. `zap_pte_range` 调用 `unlikely` 后跳过 `page_remove_rmap`（mm/memory.c:1446）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`addr、page、ptent、vma` 在 `zap_pte_range` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `unlikely` 后把 `delay_rmap` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `addr、page、ptent、vma` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 1446 行调用 `unlikely` 后，第 1451 行把 `delay_rmap` 设为 `0`；第 1465 行的 `page_remove_rmap`（mem 类效果）受 `delay_rmap` 控制；受它控制、有效果的调用共 2 个：`page_remove_rmap`、`print_bad_pte`
- 横向：`unlikely` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`unlikely` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.2842

## 22. `unmap_and_move_huge_page` 调用 `unlikely` 后跳过 `remove_migration_ptes`（mm/migrate.c:1424）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`rc、src` 在 `unmap_and_move_huge_page` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `unlikely` 后把 `page_was_mapped` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `rc、src` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 1424 行调用 `unlikely` 后，第 1431 行把 `page_was_mapped` 设为 `1`；第 1441 行的 `remove_migration_ptes`（mem 类效果）受 `page_was_mapped` 控制；受它控制、有效果的调用共 1 个：`remove_migration_ptes`
- 横向：`unlikely` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`unlikely` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.2842

## 23. `thread_group_cputime` 调用 `get_current` 后跳过 `need_seqretry`（kernel/sched/cputime.c:328）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`seq、sig` 在 `thread_group_cputime` 之后被使用或发布之前，必须写入已排序；公共层在调用 `get_current` 后把 `nextseq` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `seq、sig` 时，它是否写入已排序（各架构分别检查性质，不比较架构间差异）
- 依据：第 328 行调用 `get_current` 后，第 333 行把 `nextseq` 设为 `0`；第 349 行的 `need_seqretry`（barrier 类效果）受 `nextseq` 控制；受它控制、有效果的调用共 1 个：`need_seqretry`
- 横向：`get_current` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`get_current` 是否产生了“写入已排序”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.2396

## 24. `try_charge_memcg` 调用 `get_current` 后跳过 `memcg_memory_event`（mm/memcontrol.c:2732）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`mem_over_limit` 在 `try_charge_memcg` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `get_current` 后把 `raised_max_event` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `mem_over_limit` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 2732 行调用 `get_current` 后，第 2739 行把 `raised_max_event` 设为 `true`；第 2811 行的 `memcg_memory_event`（mem 类效果）受 `raised_max_event` 控制；受它控制、有效果的调用共 1 个：`memcg_memory_event`
- 横向：`get_current` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`get_current` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.2396

