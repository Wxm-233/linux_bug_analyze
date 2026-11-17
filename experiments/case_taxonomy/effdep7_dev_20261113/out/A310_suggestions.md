# 人工分析建议（纵向信号 + 效果对上效果 + 同一资源）：A310

接口 8019 个；纵向候选 5 个，其中有横向差异的 3 个（只用于排序，不是判错依据）。以下为前 50 条。

## 1. `post_alloc_hook` 调用 `tag_clear_highpage` 后跳过 `kasan_has_integrated_init`（mm/page_alloc.c:1471）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`page` 在 `post_alloc_hook` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `tag_clear_highpage` 后把 `init` 设为 `false`，不再自己保证
- 动态阶段可检查：后续使用 `page` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 1471 行调用 `tag_clear_highpage` 后，第 1474 行把 `init` 设为 `false`；第 1479 行的 `kasan_has_integrated_init`（mem 类效果）受 `init` 控制；受它控制、有效果的调用共 2 个：`kasan_has_integrated_init`、`kernel_init_pages`
- 效果对上效果：被跳过的工作属于 mem 类；`tag_clear_highpage` 的实现有 mem 类（按架构：arm64 mem）；重合 mem
- 横向：`tag_clear_highpage` 平凡定义的架构 alpha、arc、arm、csky、hexagon、loongarch、m68k、microblaze；非平凡的 arm64（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`tag_clear_highpage` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 6.0

## 2. `kvm_get_dirty_log_protect` 调用 `kvm_arch_sync_dirty_log` 后跳过 `kvm_flush_remote_tlbs_memslot`（virt/kvm/kvm_main.c:2226）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`kvm、memslot` 在 `kvm_get_dirty_log_protect` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `kvm_arch_sync_dirty_log` 后把 `flush` 设为 `false`，不再自己保证
- 动态阶段可检查：后续使用 `kvm、memslot` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 2226 行调用 `kvm_arch_sync_dirty_log` 后，第 2229 行把 `flush` 设为 `false`；第 2264 行的 `kvm_flush_remote_tlbs_memslot`（mem 类效果）受 `flush` 控制；受它控制、有效果的调用共 1 个：`kvm_flush_remote_tlbs_memslot`
- 效果对上效果：被跳过的工作属于 mem 类；`kvm_arch_sync_dirty_log` 的实现有 mem 类（按架构：s390 mem）；重合 mem
- 横向：`kvm_arch_sync_dirty_log` 平凡定义的架构 arm64、loongarch、mips、powerpc、riscv；非平凡的 s390、x86（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`kvm_arch_sync_dirty_log` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 3.7856

## 3. `kvm_clear_dirty_log_protect` 调用 `kvm_arch_sync_dirty_log` 后跳过 `kvm_flush_remote_tlbs_memslot`（virt/kvm/kvm_main.c:2348）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`kvm、memslot` 在 `kvm_clear_dirty_log_protect` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `kvm_arch_sync_dirty_log` 后把 `flush` 设为 `false`，不再自己保证
- 动态阶段可检查：后续使用 `kvm、memslot` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 2348 行调用 `kvm_arch_sync_dirty_log` 后，第 2350 行把 `flush` 设为 `false`；第 2381 行的 `kvm_flush_remote_tlbs_memslot`（mem 类效果）受 `flush` 控制；受它控制、有效果的调用共 1 个：`kvm_flush_remote_tlbs_memslot`
- 效果对上效果：被跳过的工作属于 mem 类；`kvm_arch_sync_dirty_log` 的实现有 mem 类（按架构：s390 mem）；重合 mem
- 横向：`kvm_arch_sync_dirty_log` 平凡定义的架构 arm64、loongarch、mips、powerpc、riscv；非平凡的 s390、x86（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`kvm_arch_sync_dirty_log` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 3.7856

## 4. `__irq_set_trigger` 调用 `mask_irq` 后跳过 `unmask_irq`（kernel/irq/manage.c:980）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`desc` 在 `__irq_set_trigger` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `mask_irq` 后把 `unmask` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `desc` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 980 行调用 `mask_irq` 后，第 982 行把 `unmask` 设为 `1`；第 1013 行的 `unmask_irq`（mem 类效果）受 `unmask` 控制；受它控制、有效果的调用共 1 个：`unmask_irq`
- 效果对上效果：被跳过的工作属于 mem 类；`mask_irq` 的实现有 mem 类（按架构：仅 riscv 事实）；重合 mem
- 横向：`mask_irq` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`mask_irq` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.9464

## 5. `check_stack_read_fixed_off` 调用 `verbose` 后跳过 `push_jmp_history`（kernel/bpf/verifier.c:4923）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`env` 在 `check_stack_read_fixed_off` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `verbose` 后把 `insn_flags` 设为 `0`，不再自己保证
- 动态阶段可检查：后续使用 `env` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 4923 行调用 `verbose` 后，第 4930 行把 `insn_flags` 设为 `0`；第 4933 行的 `push_jmp_history`（mem 类效果）受 `insn_flags` 控制；受它控制、有效果的调用共 1 个：`push_jmp_history`
- 效果对上效果：被跳过的工作属于 mem 类；`verbose` 的实现有 mem 类（按架构：仅 riscv 事实）；重合 mem
- 横向：`verbose` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`verbose` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.3212

