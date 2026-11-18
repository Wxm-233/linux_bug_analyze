# 新疑点的 lore 核对（2026-11-18）

人机验证由用户本人在浏览器面板里通过，搜索由 Claude 完成。

| 疑点 | 搜索 | 结果 |
|---|---|---|
| riscv `__kernel_map_pages` 在关中断时经 `flush_tlb_kernel_range` 发 IPI 并等待（审查第 2 条） | linux-riscv：`b:__kernel_map_pages b:flush_tlb_kernel_range`；all：`b:debug_pagealloc b:riscv b:smp_call_function_many_cond d:20240501..` | **没人报过**。<br>- Nam Cao 2024-05《riscv: rewrite __kernel_map_pages() to fix sleeping in invalid context》（就是开发样本 fb1cf0878328）引入了这次 `flush_tlb_kernel_range` 调用；讨论里只谈了睡眠，Alexandre Ghiti 给了 Reviewed-by，没人提关中断时的 IPI。他们在默认的 QEMU virt 上测试，那里 IPI 走 SBI，看不到这个告警。<br>- Mike Rapoport 2026-07-21《[PATCH RFC 15/18] riscv: convert set_memory to the generic CPA implementation》（还在审）没有改 `__kernel_map_pages`，所以不会顺带修掉。 |
| kgdb 撤销软件断点时 `flush_icache_range` 在 riscv、arc 上走 `on_each_cpu(…, 1)`（审查第 12、13 条） | all：`b:kgdb b:flush_icache_range b:on_each_cpu d:20200101..` | **没人报过**。只搜到删除整个架构（sh、nds32）的补丁里顺带出现这些词。 |
| sh SH-X3 多核 `aio_complete` 关中断时 `flush_dcache_folio` 发 IPI（审查第 4 条） | 未单独搜索 | 影响面很小（只有 SH-X3 多核），暂不报告。 |

链接：
- https://lore.kernel.org/linux-riscv/fd2100a8-a17c-460c-a8e8-b5cede3d51c1@ghiti.fr/T/
- https://lore.kernel.org/linux-riscv/20260721-generic-set-memory-v0-1-v1-15-2c1fc62306b3@kernel.org/
