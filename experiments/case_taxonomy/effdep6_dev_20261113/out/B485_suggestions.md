# 人工分析建议（纵向信号 + 效果对上效果）：B485

接口 7989 个；纵向候选 9 个，其中有横向差异的 3 个（只用于排序，不是判错依据）。以下为前 50 条。

## 1. `post_alloc_hook` 调用 `tag_clear_highpage` 后跳过 `kasan_has_integrated_init`（mm/page_alloc.c:1534）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`order、page` 在 `post_alloc_hook` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `tag_clear_highpage` 后把 `init` 设为 `false`，不再自己保证
- 动态阶段可检查：后续使用 `order、page` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 1534 行调用 `tag_clear_highpage` 后，第 1537 行把 `init` 设为 `false`；第 1542 行的 `kasan_has_integrated_init`（mem 类效果）受 `init` 控制；受它控制、有效果的调用共 2 个：`kasan_has_integrated_init`、`kernel_init_pages`
- 效果对上效果：被跳过的工作属于 mem 类；`tag_clear_highpage` 的实现有 mem 类（按架构：arm64 mem）；重合 mem
- 横向：`tag_clear_highpage` 平凡定义的架构 alpha、arc、arm、csky、hexagon、loongarch、m68k、microblaze；非平凡的 arm64（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`tag_clear_highpage` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 6.0

## 2. `kvm_get_dirty_log_protect` 调用 `kvm_arch_sync_dirty_log` 后跳过 `kvm_flush_remote_tlbs_memslot`（virt/kvm/kvm_main.c:2179）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`kvm、memslot` 在 `kvm_get_dirty_log_protect` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `kvm_arch_sync_dirty_log` 后把 `flush` 设为 `false`，不再自己保证
- 动态阶段可检查：后续使用 `kvm、memslot` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 2179 行调用 `kvm_arch_sync_dirty_log` 后，第 2182 行把 `flush` 设为 `false`；第 2217 行的 `kvm_flush_remote_tlbs_memslot`（mem 类效果）受 `flush` 控制；受它控制、有效果的调用共 1 个：`kvm_flush_remote_tlbs_memslot`
- 效果对上效果：被跳过的工作属于 mem 类；`kvm_arch_sync_dirty_log` 的实现有 mem 类（按架构：s390 mem）；重合 mem
- 横向：`kvm_arch_sync_dirty_log` 平凡定义的架构 arm64、loongarch、mips、powerpc、riscv；非平凡的 s390、x86（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`kvm_arch_sync_dirty_log` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 3.7856

## 3. `kvm_clear_dirty_log_protect` 调用 `kvm_arch_sync_dirty_log` 后跳过 `kvm_flush_remote_tlbs_memslot`（virt/kvm/kvm_main.c:2301）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`kvm、memslot` 在 `kvm_clear_dirty_log_protect` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `kvm_arch_sync_dirty_log` 后把 `flush` 设为 `false`，不再自己保证
- 动态阶段可检查：后续使用 `kvm、memslot` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 2301 行调用 `kvm_arch_sync_dirty_log` 后，第 2303 行把 `flush` 设为 `false`；第 2334 行的 `kvm_flush_remote_tlbs_memslot`（mem 类效果）受 `flush` 控制；受它控制、有效果的调用共 1 个：`kvm_flush_remote_tlbs_memslot`
- 效果对上效果：被跳过的工作属于 mem 类；`kvm_arch_sync_dirty_log` 的实现有 mem 类（按架构：s390 mem）；重合 mem
- 横向：`kvm_arch_sync_dirty_log` 平凡定义的架构 arm64、loongarch、mips、powerpc、riscv；非平凡的 s390、x86（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`kvm_arch_sync_dirty_log` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 3.7856

## 4. `acpi_os_read_memory` 调用 `acpi_os_ioremap` 后跳过 `rcu_read_unlock`（drivers/acpi/osl.c:732）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`（资源未识别）` 在 `acpi_os_read_memory` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `acpi_os_ioremap` 后把 `unmap` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `该资源` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 732 行调用 `acpi_os_ioremap` 后，第 735 行把 `unmap` 设为 `true`；第 747 行的 `rcu_read_unlock`（mem 类效果）受 `unmap` 控制；受它控制、有效果的调用共 1 个：`rcu_read_unlock`
- 效果对上效果：被跳过的工作属于 mem 类；`acpi_os_ioremap` 的实现有 mem 类（按架构：仅 riscv 事实）；重合 mem
- 横向：`acpi_os_ioremap` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`acpi_os_ioremap` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 1.7408

## 5. `acpi_os_write_memory` 调用 `acpi_os_ioremap` 后跳过 `rcu_read_unlock`（drivers/acpi/osl.c:763）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`（资源未识别）` 在 `acpi_os_write_memory` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `acpi_os_ioremap` 后把 `unmap` 设为 `true`，不再自己保证
- 动态阶段可检查：后续使用 `该资源` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 763 行调用 `acpi_os_ioremap` 后，第 766 行把 `unmap` 设为 `true`；第 789 行的 `rcu_read_unlock`（mem 类效果）受 `unmap` 控制；受它控制、有效果的调用共 1 个：`rcu_read_unlock`
- 效果对上效果：被跳过的工作属于 mem 类；`acpi_os_ioremap` 的实现有 mem 类（按架构：仅 riscv 事实）；重合 mem
- 横向：`acpi_os_ioremap` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`acpi_os_ioremap` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 1.7408

## 6. `__irq_set_trigger` 调用 `mask_irq` 后跳过 `unmask_irq`（kernel/irq/manage.c:977）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`desc` 在 `__irq_set_trigger` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `mask_irq` 后把 `unmask` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `desc` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 977 行调用 `mask_irq` 后，第 979 行把 `unmask` 设为 `1`；第 1010 行的 `unmask_irq`（mem 类效果）受 `unmask` 控制；受它控制、有效果的调用共 1 个：`unmask_irq`
- 效果对上效果：被跳过的工作属于 mem 类；`mask_irq` 的实现有 mem 类（按架构：仅 riscv 事实）；重合 mem
- 横向：`mask_irq` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`mask_irq` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.9464

## 7. `migrate_pages` 调用 `memset` 后跳过 `list_cut_before`（mm/migrate.c:2044）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`folio2、folios、from` 在 `migrate_pages` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `memset` 后把 `nr_pages` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `folio2、folios、from` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 2044 行调用 `memset` 后，第 2052 行把 `nr_pages` 设为 `0`；第 2065 行的 `list_cut_before`（mem 类效果）受 `nr_pages` 控制；受它控制、有效果的调用共 2 个：`list_cut_before`、`list_splice_init`
- 效果对上效果：被跳过的工作属于 mem 类；`memset` 的实现有 mem 类（按架构：arm mem；arm64 mem；loongarch mem；powerpc mem）；重合 mem
- 横向：`memset` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`memset` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3468

## 8. `check_stack_read_fixed_off` 调用 `verbose` 后跳过 `push_insn_history`（kernel/bpf/verifier.c:5109）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`env` 在 `check_stack_read_fixed_off` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `verbose` 后把 `insn_flags` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `env` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 5109 行调用 `verbose` 后，第 5116 行把 `insn_flags` 设为 `0`；第 5119 行的 `push_insn_history`（mem 类效果）受 `insn_flags` 控制；受它控制、有效果的调用共 1 个：`push_insn_history`
- 效果对上效果：被跳过的工作属于 mem 类；`verbose` 的实现有 mem 类（按架构：仅 riscv 事实）；重合 mem
- 横向：`verbose` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`verbose` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3209

## 9. `convert_ctx_accesses` 调用 `verbose` 后跳过 `bpf_patch_insn_data`（kernel/bpf/verifier.c:19927）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`env、insn_buf` 在 `convert_ctx_accesses` 之后被使用或发布之前，必须缓存已同步、已写入（清零或初始化）、页表项已设置、TLB 已刷新；公共层在调用 `verbose` 后把 `cnt` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `env、insn_buf` 时，它是否缓存已同步、已写入（清零或初始化）、页表项已设置、TLB 已刷新（各架构分别检查性质，不比较架构间差异）
- 依据：第 19927 行调用 `verbose` 后，第 19931 行把 `cnt` 设为 `0`；第 19955 行的 `bpf_patch_insn_data`（cache+mem+pgtable+tlb 类效果）受 `cnt` 控制；受它控制、有效果的调用共 1 个：`bpf_patch_insn_data`
- 效果对上效果：被跳过的工作属于 cache+mem+pgtable+tlb 类；`verbose` 的实现有 mem 类（按架构：仅 riscv 事实）；重合 mem
- 横向：`verbose` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`verbose` 是否产生了“缓存已同步、已写入（清零或初始化）、页表项已设置、TLB 已刷新”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3209

