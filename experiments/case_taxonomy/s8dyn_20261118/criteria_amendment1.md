# 判据修订 1（第一轮运行之后、最终判定之前写下）

2026-11-18，Claude。

**原因**：第一轮（`runs/main`、`judge_main.txt`）里，开了 `aia=aplic-imsic` 的三格（A、B、C）9 次运行全部出现 RCU stall，卡在 `imsic_local_timer_callback`；这包括预测不会出问题的 B（修复变异）和 C（`debug_pagealloc=off`）。所以这是 QEMU 8.2 的 IMSIC 在 TCG 下的环境问题，与疑点无关。当时主机负载很重：5 个 QEMU 并行，另有留出集检验的 4 个分析进程。不开 AIA 的 D、E 两格 6 次全部正常结束。

另外，有几次运行已经到了 `reboot: Power down`，日志里却找不到 `@@END`，`@@WORKER 0` 那一行也不见了，怀疑串口输出被大量 stall 信息挤掉了。

A 格第 1 次已经命中：`kernel/smp.c:925` 的 `WARN_ON_ONCE(!in_task())`，调用栈为
`kmem_cache_free`（RCU 软中断）→ … → `allocate_slab` → `prep_new_page` → `__kernel_map_pages` → `flush_tlb_kernel_range` → `__flush_tlb_range` → `on_each_cpu_cond_mask` → `smp_call_function_many_cond`；
寄存器 `status=…0120`，其中 SIE 位为 0，说明当时中断是关着的。

**更正判据第一节的一处说法**：当前版本里，`smp_call_function_many_cond` 对“关中断时调用”的检查是 `lockdep_assert_irqs_enabled()`，只在打开 lockdep 时生效；不开 lockdep 时能看到的是紧接着的 `WARN_ON_ONCE(!in_task())`（软中断或硬中断上下文里调用）。两者都是“在不允许的上下文里发 IPI 并等待”，源码注释说两者都可能死锁。判定标准“`kernel/smp.c` 的 WARNING，且 40 行内的调用栈含 `__kernel_map_pages`”不变。

**改动**：
1. 等留出集检验结束、主机空闲后，**重跑 A、B、C 三格**，每格 3 次，并行度降为 2，超时提高到 600 秒，结果记为 `runs/aia2`。D、E 两格沿用第一轮的结果。
2. 有效运行的条件补充一条：日志里出现 `reboot: Power down`，并且有至少 3 行 `@@WORKER`，也算正常结束（串口可能丢了 `@@END`）。
3. 如果重跑后 B、C 仍然出现 stall、无法正常结束，就按“环境不支持”报告：A 格的命中作为观察记录，不判定为“确认”。
