# 动态验证新疑点：riscv `__kernel_map_pages` 在关中断时发 IPI 并等待（判据，构建和运行之前定下）

2026-11-18，Claude。来源：`ctxeff_20261118` 审查第 2 条（裁定“可能”，两人有分歧）。用户：“继续吧”（续跑留出集，接着按停点做动态验证）。

## 一、疑点

- 当前版本 df2908090cda 的 riscv `__kernel_map_pages`（`arch/riscv/mm/pageattr.c:421`），在改完页表后调用 `flush_tlb_kernel_range(start, start + size)`。
- 多核、并且 IPI 不走 SBI（`riscv_use_sbi_for_rfence()` 为假）时，`__flush_tlb_range` 会调用 `on_each_cpu_mask(…, 1)`。
- `__kernel_map_pages` 可能在关中断时被调用（`spin_lock_irqsave` 里做 GFP_ATOMIC 分配、关中断时释放页）。这时 `kernel/smp.c` 的 `smp_call_function_many_cond` 会触发 `WARN_ON_ONCE(cpu_online(this_cpu) && irqs_disabled() && …)`，还可能死锁。

## 二、内核（kbuild）

- 新配置档 `dpa`：defconfig + `DEBUG_KERNEL`、`DEBUG_PAGEALLOC`、`RISCV_APLIC`、`RISCV_APLIC_MSI`、`RISCV_IMSIC`。不开 `DEBUG_PAGEALLOC_ENABLE_DEFAULT`，运行时用启动参数控制。
- 修复变异 F8（`mutations/s8dyn.json`）：把 riscv `__kernel_map_pages` 里的 `flush_tlb_kernel_range(` 换成 `local_flush_tlb_kernel_range(`。这和上游对 kfence 同型问题的修法（b3431a8bb336）一致；它只用于归因，不是上游修复。
- 内核：riscv `dpa`、riscv `dpa` + F8、x86_64 `dpa`（对照）。

## 三、运行

- `/init` 是一个静态程序（`s8.c`），产生分配和释放的负载：fork、管道、mmap 后写入再 munmap、读 `/proc`，持续约 20 秒。然后打印 `@@END`，关机。
- QEMU：
  - riscv：`-M virt,aia=aplic-imsic`（S 态 IPI 走 IMSIC，不走 SBI）或 `-M virt`（不开 AIA，IPI 走 SBI）；`-smp 4 -m 2G`；
  - x86_64：`-smp 4 -m 2G`。
- 启动参数：`debug_pagealloc=on` 或 `off`。
- 每格跑 3 次，超时 300 秒。

## 四、判定

- **有效运行**：日志里出现 `@@END`，或者在 `@@END` 之前就因告警或死锁中止（中止也记录下来）。
- **命中**：日志里出现 `WARNING: … kernel/smp.c`，并且其后 40 行的调用栈里含 `__kernel_map_pages`。另外单独记录：死锁（超时且没有 `@@END`）、其他和 `__kernel_map_pages` 有关的告警。

## 五、预测

| 格 | 内核 | 机器 | debug_pagealloc | 预测 |
|---|---|---|---|---|
| A | riscv dpa | aia=aplic-imsic | on | **命中 3/3** |
| B | riscv dpa + F8 | aia=aplic-imsic | on | 0/3 |
| C | riscv dpa | aia=aplic-imsic | off | 0/3 |
| D | riscv dpa | virt（IPI 走 SBI） | on | 0/3 |
| E | x86_64 dpa | 默认 | on | 0/3 |

**判定标准**：
- 5 格的预测全部符合，就判这个疑点为**确认**；
- A 格 0/3，就判这个疑点**不成立**（至少在 QEMU 上）；
- 其他情况如实报告，不确认。
