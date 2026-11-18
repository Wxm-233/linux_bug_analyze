# 动态验证新疑点：riscv `__kernel_map_pages` 在不允许的上下文里发 IPI 并等待（s8dyn_20261118）

2026-11-18，Claude。来源：调用上下文检查 `ctxeff_20261118` 审查第 2 条。
- 判据 `criteria.md`；修订 1（低负载重跑、补充“正常结束”的认定）和修订 2（改用单线程 TCG），都写在最终判定之前。三份的 SHA 记在 `criteria_sha256.txt`。
- 内核用 kbuild 构建：新配置档 `dpa`（defconfig + `DEBUG_KERNEL`、`DEBUG_PAGEALLOC`、riscv AIA 驱动），变异 `mutations/s8dyn.json:F8`。

统计行：模型调用 0；Codex 调用 0；构建 3（riscv dpa、riscv dpa+F8、x86_64 dpa）；运行 39 次（15 + 9 + 9，另有 2 次环境探测不计）。

## 一句话结论

**证据很强，但按事先定的判据，还够不上“确认”。**
- 开了 IMSIC（S 态 IPI 不走 SBI）、打开 `debug_pagealloc` 的 riscv 内核，9 次运行里有 5 次直接表现出这个缺陷：4 次 `kernel/smp.c` 告警，1 次卡死在 `__kernel_map_pages` 发出的 IPI 等待里。调用栈都是同一条：页分配 → `prep_new_page` → `__kernel_map_pages` → `flush_tlb_kernel_range` → `on_each_cpu_cond_mask` → `smp_call_function_many_cond`。
- 修复变异、关掉 `debug_pagealloc`、IPI 走 SBI、x86 这四种对照，合计 24 次运行，**一次都没有**。
- 没有判为“确认”的原因：最后一轮 A 格预测 3/3 命中告警，实际是 2 次告警加 1 次死锁；B、C 各有 1 次因 QEMU 环境问题卡住，没有正常结束。

## 疑点

- riscv 的 `__kernel_map_pages`（debug_pagealloc 用来在页分配和释放时映射或取消映射直接映射区）改完页表后，调用 `flush_tlb_kernel_range`。
- 在多核、并且 IPI 不走 SBI（有 IMSIC 或 ACLINT 的硬件）时，`flush_tlb_kernel_range` 会调用 `on_each_cpu_mask(…, wait=1)`，向其他 CPU 发 IPI 并等待它们完成。
- 而 `__kernel_map_pages` 会在软中断里、或者关中断时被调用，比如 slab 在 `local_lock_irqsave` 里补充对象时取新页。在这种上下文里发 IPI 并等待是不允许的：
  - `smp_call_function_many_cond` 里有 `WARN_ON_ONCE(!in_task())`（软中断或硬中断里调用）；
  - 还有 `lockdep_assert_irqs_enabled()`（关中断时调用，打开 lockdep 才检查）；
  - 源码注释写明两者都可能死锁。
- 旁证：
  - x86 的同名函数里有注释：“We should perform an IPI and flush all tlbs, but that can deadlock, settle for a local flush”；
  - kfence 的同型问题（riscv `kfence_protect_page` 关中断时刷 TLB）已由 b3431a8bb336 改成只刷本地；
  - 这一处是 fb1cf0878328（2024-05，修 `__kernel_map_pages` 会睡眠的问题）引入的。当时在默认的 QEMU virt 上测试，那里 IPI 走 SBI，看不到这个问题。
- lore 上没人报过（见 `ctxeff_20261118/lore_check.md`）。

## 结果（`summary.json`、`judge_*.txt`、`runs/`）

| 格 | 内核 / 机器 / 启动参数 | 告警命中 | 卡在 `__kernel_map_pages` 的 IPI 等待 | 正常结束 | 其他卡住（环境） |
|---|---|---|---|---|---|
| A | riscv dpa，`aia=aplic-imsic`，`debug_pagealloc=on` | **4/9** | **1/9** | 2 | 2 |
| B | riscv dpa + F8（只刷本地），同 A | 0/9 | 0 | 3 | 6 |
| C | riscv dpa，`aia=aplic-imsic`，`debug_pagealloc=off` | 0/9 | 0 | 4 | 5 |
| D | riscv dpa，`virt`（IPI 走 SBI），`debug_pagealloc=on` | 0/3 | 0 | 3 | 0 |
| E | x86_64 dpa，`debug_pagealloc=on` | 0/3 | 0 | 3 | 0 |

A、B、C 三格跑了三轮：
- 第一轮：5 个 QEMU 加上留出集检验同时运行；
- 第二轮：降低并行度；
- 第三轮：改用单线程 TCG。

开 IMSIC 的格子在多线程 TCG 下普遍出现 RCU stall，连 B、C 也一样；环境探测证实这是 QEMU 8.2 的多线程 TCG 和 IMSIC 的组合问题（修订 2）。B、C 的卡住，调用栈里都没有 IPI 等待；A 格卡住的那次，调用栈停在 `smp_call_function_many_cond`，来自 `__kernel_map_pages`。

**典型告警**（`runs/main/A.run1.log`）：
```
WARNING: kernel/smp.c:925 at smp_call_function_many_cond+0x474/0x67c, CPU#3: ksoftirqd/3/32
 smp_call_function_many_cond ← on_each_cpu_cond_mask ← __flush_tlb_range ← flush_tlb_kernel_range
 ← __kernel_map_pages ← prep_new_page ← get_page_from_freelist ← __alloc_frozen_pages_noprof ← allocate_slab
 ← refill_objects ← __pcs_replace_empty_main ← __kmalloc_flags_noprof ← … ← kmem_cache_free ← kernfs_free_rcu
 ← rcu_core ← handle_softirqs ← run_ksoftirqd
```
寄存器 `status=…0120` 中 SIE 为 0，说明当时中断是关着的。

**按事先判据的判定**（最终判定用第三轮的 A、B、C，加第一轮的 D、E）：
- A：2/3 命中告警，第 3 次卡在 `__kernel_map_pages` 的 IPI 等待里。预测是 3/3 命中，**不符**；
- B、C：0 命中，符合，但各有 1 次没正常结束；
- D、E：0/3，符合。

所以**不判为“确认”**。如果把“卡在 `__kernel_map_pages` 的 IPI 等待里”也算作疑点的表现（判据第四节只要求把它单独记录），A 就是 3/3。这一点留给用户决定。

## 补充：开 lockdep 一轮（修订 3，`runs/lk`、`judge_lk.txt`）

用户：“开 lockdep 补一轮”。新配置档 `dpalk` = `dpa` + `PROVE_LOCKING`；单线程 TCG，超时 900 秒。

| 格 | 告警命中 | 有效运行 | 说明 |
|---|---|---|---|
| A riscv dpalk，IMSIC，`debug_pagealloc=on` | **3/3** | 3/3 | 3 次都是 `kernel/smp.c:917`，即 `lockdep_assert_irqs_enabled()`（关中断时调用）；发生在 PID 1 的普通进程上下文里，不是软中断。调用栈 3 次相同：`prep_new_page → __kernel_map_pages → flush_tlb_kernel_range → __flush_tlb_range → smp_call_function_many_cond`；lockdep 指出中断是在 `_raw_spin_lock_irqsave` 处关掉的 |
| B 加 F8 | 0/3 | 2/3 | 第 3 次是环境 stall（调用栈里没有 IPI 等待） |
| C `debug_pagealloc=off` | 0/3 | **0/3** | 3 次都超时：开 lockdep 后运行慢，再加上 IMSIC 环境 stall；调用栈里都没有 IPI 等待 |

**判定**：
- 告警次数与预测全部一致：A 3/3，B、C 都是 0。
- 但判定脚本按严格口径要求每格都是有效运行，C 格这一轮没有一次有效运行，所以**按事先判据仍不能写“确认”**。
- C 格（`debug_pagealloc=off`）这一对照，在前两轮单线程和多线程运行里有 7 次正常结束，0 次命中。
- 这一轮最关键的新证据：不开 lockdep 时，只能看到“在软中断里调用”这一种情况；开了以后，3/3 都直接报出“**关中断时调用**”，正好对上静态分析 X2 规则的判断；并且 lockdep 给出了关中断的位置。
- 最新主线（master `7ccb044c2772`）上，riscv `__kernel_map_pages` 和 `__flush_tlb_range` 的代码与 7.3-rc2 相同，问题依然存在（只核对了源码，没有在最新主线上运行）。

## 补充：补跑 B、C 两格（修订 4，`runs/lk2`、`run_lk2.log`）

用户：“补跑 C 格”。B、C 两格同时进行，每格一次只跑一个，超时 1500 秒，累计 3 次有效运行就停，最多尝试 6 次。

| 格 | 尝试 | 有效 | 命中 |
|---|---|---|---|
| B 加 F8 | 6 | 2 | 0 |
| C `debug_pagealloc=off` | 6 | **0** | 0 |

**按修订 4 判为“环境不支持”，不写“确认”。** 无效运行全部是 RCU stall 后超时，大多数都有一个工作进程始终没结束。C 格第 1 次 stall 时的调用栈里出现了与 `__kernel_map_pages` 无关的 IPI 等待，说明在 QEMU 8.2 的 IMSIC 环境下，IPI 投递本身就不可靠。

## 最终汇总（全部轮次）

| | 运行次数 | `kernel/smp.c` 告警且栈中有 `__kernel_map_pages` | 卡在 `__kernel_map_pages` 的 IPI 等待 |
|---|---|---|---|
| A（riscv、IMSIC、`debug_pagealloc=on`） | 12 | **8**（其中开 lockdep 3/3） | 1 |
| B（F8 只刷本地） | 18 | 0 | 0 |
| C（`debug_pagealloc=off`） | 18 | 0 | 0 |
| D（IPI 走 SBI） | 3 | 0 | 0 |
| E（x86） | 3 | 0 | 0 |

**结论**：
- 疑点的表现只出现在 A 格，而且原因明确：开 lockdep 后 3/3 报“关中断时调用”，并指出关中断的位置；
- 四种对照合计 42 次，0 次出现；
- 按事先判据（每格都要凑够 3 次有效运行）没能确认，原因是 QEMU 8.2 的 IMSIC 模拟不稳定，对照格有效运行不够；
- 是否据此向上游报告，由用户决定。如果报告，邮件里要如实写明这一点。

## 判据第一节的一处更正（修订 1 已写明）

当前版本里，“关中断时调用”的检查是 `lockdep_assert_irqs_enabled()`，不开 lockdep 时看不到。实际触发的是紧接着的 `WARN_ON_ONCE(!in_task())`：调用发生在 ksoftirqd 处理软中断的过程中。

## 下一步（需要用户决定）

1. 是否当作确认缺陷，向上游报告。修法和 kfence 一样，把 `flush_tlb_kernel_range` 换成 `local_flush_tlb_kernel_range`。x86 的做法和注释可以作为依据。上游维护者大概率会讨论只刷本地是否足够：debug_pagealloc 只是调试功能，x86 也只刷本地。
2. 如果想按判据拿到“确认”：打开 lockdep（`PROVE_LOCKING`）再跑一轮，这样关中断的情况也会直接告警；或者把“卡在 IPI 等待”写成修订后的判定标准，用新的一轮来检验。

## 文件

- 判据：`criteria.md`、`criteria_amendment1.md`、`criteria_amendment2.md`、`criteria_sha256.txt`
- 构建：`build.sh`、`build_f8.sh`、`build*.log`、`kernels/*.path`；kbuild 配置档 `tools/kbuild/profiles.json:dpa`、变异 `tools/kbuild/mutations/s8dyn.json`
- 运行：`s8.c`（/init）、`run.sh`、`probe_env.sh`、`runs/{main,aia2,st,probe}/`、`run_*.log`
- 判定：`judge.py`、`judge_{main,aia2,st}.{json,txt}`、`summarize.py`、`summary.json`
