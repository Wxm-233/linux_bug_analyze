# 判据修订 3：开 lockdep 补一轮（构建和运行之前写下）

2026-11-18，Claude。用户：“开 lockdep 补一轮”。

**原因**：前三轮按判据没有达到“确认”：最后一轮 A 格是 2 次告警加 1 次死锁。当前版本里，`smp_call_function_many_cond` 对“关中断时调用”的检查是 `lockdep_assert_irqs_enabled()`，只在开了 lockdep 时生效。打开以后，疑点中“关中断时发 IPI 并等待”这一半也会直接告警，不再只依赖 `WARN_ON_ONCE(!in_task())`，也就是不再只靠“恰好在软中断里”这一种情况。

**这一轮的设置**：
- 新 kbuild 配置档 `dpalk` = `dpa` + `PROVE_LOCKING`（会自动打开 lockdep）；
- 内核：riscv `dpalk`、riscv `dpalk` + F8。F8 与前几轮相同；
- 机器：`-M virt,aia=aplic-imsic -accel tcg,thread=single -smp 4 -m 2G`；超时 900 秒，因为 lockdep 会让运行变慢；并行 3；
- 结果记为 `runs/lk`。

| 格 | 内核 | debug_pagealloc | 预测 |
|---|---|---|---|
| A | riscv dpalk | on | **命中 3/3** |
| B | riscv dpalk + F8 | on | 0/3 |
| C | riscv dpalk | off | 0/3 |

**判定**：
- **命中**的定义同前：`kernel/smp.c` 的 WARNING，并且其后 40 行内的调用栈含 `__kernel_map_pages`。
- **有效运行**同修订 1。
- 三格的预测全部符合，就判这个疑点为**确认**。
- 前三轮的结果作为背景，不和这一轮合并计算。

**已知风险，事先写明**：
- lockdep 一旦先报出别的锁问题，就会关掉自己（`debug_locks=0`），此后 `lockdep_assert_irqs_enabled` 不再检查；不过 `WARN_ON_ONCE(!in_task())` 不受影响。
- 两条检查都是 `WARN_ON_ONCE`：每个启动的内核最多各打印一次。
- 如果出现 lockdep 关掉自己的情况，如实记录。
