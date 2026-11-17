# 人工分析建议（纵向信号 + 效果对上效果 + 同一资源）：A032

接口 8286 个；纵向候选 2 个，其中有横向差异的 1 个（只用于排序，不是判错依据）。以下为前 50 条。

## 1. `post_alloc_hook` 调用 `tag_clear_highpage` 后跳过 `kasan_has_integrated_init`（mm/page_alloc.c:1515）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`page` 在 `post_alloc_hook` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `tag_clear_highpage` 后把 `init` 设为 `false`，不再自己保证
- 动态阶段可检查：后续使用 `page` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 1515 行调用 `tag_clear_highpage` 后，第 1518 行把 `init` 设为 `false`；第 1523 行的 `kasan_has_integrated_init`（mem 类效果）受 `init` 控制；受它控制、有效果的调用共 2 个：`kasan_has_integrated_init`、`kernel_init_pages`
- 效果对上效果：被跳过的工作属于 mem 类；`tag_clear_highpage` 的实现有 mem 类（按架构：arm64 mem）；重合 mem
- 横向：`tag_clear_highpage` 平凡定义的架构 alpha、arc、arm、csky、hexagon、loongarch、m68k、microblaze；非平凡的 arm64（有横向差异，用于定向）
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`tag_clear_highpage` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 6.0

## 2. `__irq_set_trigger` 调用 `mask_irq` 后跳过 `unmask_irq`（kernel/irq/manage.c:972）

- 可能的缺陷类型：效果依赖（纵向：公共层相信架构接口已经产生效果，跳过自己的同类工作）
- 依赖性质：`desc` 在 `__irq_set_trigger` 之后被使用或发布之前，必须已写入（清零或初始化）；公共层在调用 `mask_irq` 后把 `unmask` 设为 `1`，不再自己保证
- 动态阶段可检查：后续使用 `desc` 时，它是否已写入（清零或初始化）（各架构分别检查性质，不比较架构间差异）
- 依据：第 972 行调用 `mask_irq` 后，第 974 行把 `unmask` 设为 `1`；第 1005 行的 `unmask_irq`（mem 类效果）受 `unmask` 控制；受它控制、有效果的调用共 1 个：`unmask_irq`
- 效果对上效果：被跳过的工作属于 mem 类；`mask_irq` 的实现有 mem 类（按架构：仅 riscv 事实）；重合 mem
- 横向：`mask_irq` 平凡定义的架构 无；非平凡的 alpha、arc、arm、arm64、csky、hexagon、loongarch、m68k
- 为什么需要人看：本轮未做动态确认
- 建议怎么查：在平凡定义的架构上，`mask_irq` 是否产生了“已写入（清零或初始化）”；如果没有，看这条路径之后还有没有别处保证。都没有，依赖就会被违反
- 得分 0.9464

