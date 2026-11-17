# 判据：检查三①执行上下文，第一版（checks_v1_20261108）

2026-11-08，Claude 在实现之前写定。写完计算 SHA256 存入 `criteria_sha256.txt`，之后不再修改；要改另写 amendment。

## 一、要回答的问题

1. 在用户收窄后的范围内，“原子上下文中做了可能睡眠、发 IPI 并等待、或拿 RT 下可睡眠的锁”这类失配，能否用纯静态分析保守地找出来？
2. 对 6 条已知样本（见第五节），在各自**修复前**的代码上能否报出？
3. 在当前版本（v7.3-rc2）上，报出多少，其中有多少像真问题？

## 二、范围

- 架构：riscv。配置：defconfig；评估样本时按需加配置（第五节）。
- 编译单元：`compile_commands.json` 中源文件路径以 `arch/riscv/`、`kernel/`、`mm/`、`lib/`、`init/`、`drivers/irqchip/`、`drivers/perf/`、`drivers/acpi/riscv/`、`drivers/clocksource/`、`drivers/iommu/riscv/`、`drivers/cpuidle/`、`drivers/firmware/` 开头的 `.c` 单元。头文件中的内联函数随所在单元一起分析。
- 范围外的单元不分析。它们中的调用者带来的原子上下文会漏，这是收窄范围的已知代价。

## 三、定义

### 3.1 上下文状态

每个程序点的状态是四个计数 `(irq, raw, spin, preempt)` 构成的元组，每个计数上限为 2。分析保存“可能的状态集合”，集合在控制流汇合处取并。

- **硬原子**：`irq>0` 或 `raw>0`（关中断、持 raw 自旋锁）。
- **原子**：硬原子，或 `spin>0`、`preempt>0`。

### 3.2 原语表（按被调函数名或宏展开后的被调函数名识别）

- **关/开中断**：`arch_local_irq_disable`、`arch_local_irq_save`、`local_irq_disable`、`local_irq_save`、`raw_local_irq_*` 等使 irq+1，对应的 enable/restore 使 irq−1。
- **raw 自旋锁**：`raw_spin_lock*`、`_raw_spin_lock*`、`arch_spin_lock` 使 raw+1；`raw_spin_trylock*` 视为可能+1；unlock 使 raw−1。
- **普通自旋锁 spinlock_t / rwlock**：`spin_lock*`、`read_lock*`、`write_lock*` 使 spin+1，unlock 使 spin−1；带 `_irq`、`_irqsave` 的同时使 irq+1。
- **禁抢占**：`preempt_disable*`、`get_cpu`、`__preempt_count_add`、`local_bh_disable` 使 preempt+1，对应的 enable 使 preempt−1。
- **可能睡眠**（种子）：`__might_sleep`、`__might_resched`、`__might_fault`、`schedule*`、`mutex_lock*`、`down`、`down_read*`、`down_write*`、`down_interruptible`、`down_killable`、`msleep*`、`usleep_range*`、`wait_for_completion*`、`synchronize_rcu*`、`flush_work`、`cancel_work_sync`、`vmalloc`、`vzalloc`、`copy_from_user`、`copy_to_user`、`_copy_from_user`、`_copy_to_user`、`get_user`、`put_user`、`cond_resched`。另外，分配函数（`kmalloc*`、`kzalloc*`、`__get_free_pages`、`alloc_pages*`）若实参文本中含 `GFP_KERNEL`、`GFP_USER`、`GFP_KERNEL_ACCOUNT`，也算可能睡眠。
- **IPI 并等待**（种子）：`smp_call_function*`、`on_each_cpu*`、`smp_call_function_many_cond`。
- **RT 下可睡眠的锁**：`spin_lock*`、`read_lock*`、`write_lock*`、`rt_spin_lock`。

### 3.3 传递性质

在本范围的调用图上（直接调用，按 USR 区分），求三个“可能”性质的闭包，并记录一条最短链：`may_sleep`、`may_ipi`、`may_rt_lock`。

- 间接调用（函数指针）不传播，单独计数。
- 原语函数本身的函数体不再展开。
- 以 `pr_`、`printk`、`dev_`、`WARN`、`BUG`、`panic`、`dump_stack`、`trace_`、`lockdep_`、`kasan_`、`kcsan_`、`kmsan_` 开头的被调函数不向下展开，沿用旧 CTX 规则修订 1 的理由。

### 3.4 原子上下文的来源

- **函数内**：按 3.1、3.2 的状态变化，在 AST 上做结构化的数据流分析，覆盖 if/else、循环（迭代到不动点）、switch、goto/label（标签状态取所有跳入来源的并）和 return。
- **函数入口**，以下各项构成“入口状态集合”：
  - (a) **陷入入口**：`arch/riscv/kernel/entry.S` 中出现、在本范围内有 C 定义的函数，入口状态含 `irq=1`。这是 RISC-V 进入异常处理时 SIE 已清零的架构事实。
  - (b) **IPI/停机回调**：作为函数指针实参传给 `smp_call_function*`、`on_each_cpu*`、`stop_machine*`、`stop_one_cpu*` 的函数，入口状态含 `irq=1`。
  - (c) **调用者传播**：其余函数的入口状态是所有调用点状态的并；没有已知调用者的，取 `(0,0,0,0)`。
  - 在本范围的调用图上迭代到不动点。

### 3.5 报告（标记）

在某个调用点，若可能状态中存在：

- **S 类**：原子状态，且被调函数 `may_sleep`；
- **I 类**：硬原子状态，且被调函数 `may_ipi`；
- **R 类**：硬原子状态，且被调函数 `may_rt_lock`。在 PREEMPT_RT 下 spinlock_t 会睡眠；本次不构建 RT 配置，按原语识别；

就报出一条标记：`{类别, 调用者, 调用位置, 被调者, 被调者的性质链, 原子状态的来源（函数内区间 / 入口 a/b/c 及传播链）}`。

`__init` 段函数中的区间不作为来源（沿用旧规则修订 1b）。

## 四、保障口径

- **相对于以下模型不漏报**：第二节的范围、第三节的原语表与入口规则、直接调用图、AST 结构化数据流。在这个模型下，任何“可能处在原子状态的调用点调用了可能睡眠的函数”都会被报出，允许误报。
- **已知不在保障内**，结果中逐项计数：
  - 间接调用；
  - 范围外的调用者；
  - 内联汇编改变中断状态；
  - 分配函数的 gfp 参数经变量传入；
  - 宏中未展开成函数调用的原语；
  - “函数返回时仍持锁”的跨函数锁状态（第一版假设非原语函数不改变调用者的状态）；
  - 未建模的上下文，例如硬中断处理函数本身、softirq、NMI、RCU 读侧。

## 五、样本评估

6 条样本（E1 中属于本检查性质的；按补丁说明确定，确定于实现之前）：

| id | 修复提交 | 性质 | 额外配置 |
| --- | --- | --- | --- |
| A076 | fb1cf0878328 | `__kernel_map_pages` 在原子上下文中经 `__set_memory` 取 init_mm 的读写信号量 | DEBUG_PAGEALLOC |
| A118 | 6a97f4118ac0 | 陷入处理中 `die()` 拿 spinlock_t（RT） | 无 |
| A122 | b3431a8bb336 | `kfence_protect_page` 在关中断时经 `flush_tlb_kernel_range` 发 IPI | KFENCE |
| A158 | 61a74ad25462 | 未对齐陷入处理中关中断调用 `copy_from_user` | 无 |
| A175 | 969f028bf2c4 | 用户态陷入处理中关中断调用 `force_sig_fault`（RT 锁） | 无 |
| A344 | 453805f0a28f | 同 A158 一族，修法是开中断 | 无 |

不在本检查范围的 E1 样本（A002、A068、A083、A102、A202、B580 插桩约定；A069、B558 要求调用方处于原子上下文；A309、A327 死锁；A350 缺锁），本轮不计。

- **评估方法**：对每条样本，在 `/root/work` 下建修复提交父版本的 git worktree，`make O=… defconfig`（加额外配置）后构建，生成编译数据库，在范围内运行检查器。
- **命中**：报出的标记中，有一条的调用位置或性质链落在修复改动的函数中，并且类别与样本性质一致：A076 为 S；A118、A175 为 R 或 S；A122 为 I；A158、A344 为 S。
- **同时检查修复后版本**：在修复提交本身上重跑，命中标记应当消失。这一项只作描述，不作硬性要求。

## 六、参考线

- 自测小样例：预期标记集合必须完全一致。样例覆盖 if/else、循环、goto、入口 (a)(b)、传递链和三类标记。
- 6 条样本命中不少于 4 条，记为“检出能力达标”。
- 当前版本 riscv defconfig 范围内的标记总数，以及按调用位置去重后的“不同问题”数，都要报告。
  - 人工核对：标记不超过 60 个时核对全部，超过则随机抽 40 个，种子 20261108。
  - 归为疑似真问题、不是、判断不了三类。疑似真问题占比不低于 25%，记为“噪声可接受”。
- 两条都满足，本轮记为达标。

## 七、交付

`selftest/`、`ctx_extract.py`、`ctx_analyze.py`、`eval_samples.sh`/`.py`、`flags_current.json`、`sample_eval.json`、`manual_review.json`、`stats.json`、`README.md`（中文，说人话，第一人称“我”）。不修改旧轮次。
