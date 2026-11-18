# 调用上下文检查（效果依赖版）（ctxeff_20261118）

2026-11-18，Claude。用户：“做调用上下文检查”。中途暂停过一次，用户“继续吧”后做完。**状态：完成。**
- 判据 `criteria.md`；修订 1 `criteria_amendment1.md`：区间规则增加“提前退出路径上的解锁不算结束”，写在两人审查和留出集检验之前。两份的 SHA 记在 `criteria_sha256.txt`。

统计行：模型调用 0；Codex 调用 1（21 条盲判，新会话，之后一周额度已用 44%）；构建 0；新确认缺陷 0；**新疑点 3（静态）**。

## 一句话结论

**按横纵两面做的调用上下文检查，开发召回 2/2；当前版本 21 条少数派候选里审出 4 条“可能”。其中 riscv 的 `__kernel_map_pages` 在关中断时发 IPI 并等待，是一个没人报过的新疑点，而且能在 QEMU 里动态验证。**

## 做法

和以前三轮调用上下文检查不同，这一轮不看某个架构内部，而是放进“效果依赖”框架，按横纵两面来做：
- **横向**：对每个“架构实现、公共代码调用”的钩子（当前版本有 1120 个），看各架构的实现沿调用链向下 4 层，会不会**睡眠**（mutex、读写信号量、GFP_KERNEL 分配等）、会不会**发 IPI 并等待**（`smp_call_function`、`on_each_cpu`、riscv SBI 远程刷新）。
- **纵向**：在公共代码里找原子区间和关中断区间（自旋锁、`local_irq_save`、`preempt_disable`、`rcu_read_lock` 等），再沿调用链向下传播 4 层。
- **规则**：
  - X1：原子上下文里调用了会睡眠的实现；
  - X2：关中断上下文里调用了会发 IPI 并等待的实现。
  - 有这个效果的架构不超过实现该钩子的架构的三分之一时，标为“少数派”，优先审查。

## 结果

### 1. 开发召回：2/2（`recall.json`）

| 修复 | 报出 |
|---|---|
| fb1cf0878328 riscv `__kernel_map_pages` 会睡眠 | X1：`__kernel_map_pages → __set_memory → mmap_write_lock`，少数派。修订 1 之前漏掉了，原因见下 |
| ce2b3a50ad92 arm64 kfence、debug_pagealloc 路径拿 mutex | X1：`kfence_protect_page`、`__kernel_map_pages → set_memory_valid → … → split_kernel_leaf_mapping → mutex_lock`，少数派 |

**修订 1 的来由**：`__alloc_pages_bulk` 里有一个“出错就解锁并 goto”的分支，纯词法的区间识别把这次解锁当成了区间结束。修订后，提前退出分支里的解锁不再计入。这个改动也带来了副作用：hugetlb 里“先解锁再调用、调用失败时重新加锁并 goto”的写法被误判为仍在区间内，造成了下面第 15～21 条误报。

### 2. 当前版本：26 条候选，其中少数派 21 条，两人盲判（`review.txt`、`claude.json`、`codex_blind/`、`adjudication.json`）

一致率 20/21。裁定：**可能 4、不可能 17**。

| 编号 | 内容 | 裁定 |
|---|---|---|
| 2 | **riscv `__kernel_map_pages` 在关中断时经 `flush_tlb_kernel_range` 发 IPI 并等待** | 可能（两人分歧，裁定为可能，见下） |
| 4 | sh（SH-X3 多核）的 `aio_complete` 在 `spin_lock_irqsave` 里调用 `flush_dcache_folio`，后者经 `smp_call_function` 等待 | 可能（影响面很小） |
| 12 | kgdb 撤销软件断点时调用 `flush_icache_range`：arc 多核走 `on_each_cpu(…, 1)`，而其他 CPU 正被关中断地圈在 kgdb 里 | 可能 |
| 13 | 同 12，riscv（IPI 不走 SBI 的平台） | 可能 |
| 1、7 | arm64 两条：上游修复（ce2b3a50ad92）后已经提前返回，词法分析看不到 | 不可能 |
| 3、6、8～11、14～21 | 示例链本身不成立：先解锁再调用、缺页路径、单核恢复、sh 在 SMP 下关闭了 kgdb 刷新、只在高端内存时等 | 不可能 |

**第 2 条为什么裁定为可能**：
- Codex 判“不可能”，理由是审查材料里的示例链（`alloc_contig` 持 zone 锁）不成立。这一点正确。
- 但真实的关中断路径很常见：
  - `spin_lock_irqsave` 里做 GFP_ATOMIC 分配：slab 取新页 → `post_alloc_hook` → `debug_pagealloc_map_pages`；
  - 关中断时释放页 → `free_pages_prepare` → `debug_pagealloc_unmap_pages`。
- riscv 的 `flush_tlb_kernel_range` 在多核、并且 IPI 不走 SBI（有 IMSIC 或 ACLINT）时，会调用 `on_each_cpu_mask(…, wait=1)`，触发 `kernel/smp.c:716` 的 `WARN_ON_ONCE(irqs_disabled())`，还可能死锁。
- x86 的同名函数里有注释，明说这里发 IPI 会死锁，所以只刷本 CPU；kfence 的同型问题（b3431a8bb336）已被上游修复。
- 这个问题是 fb1cf0878328 引入的，也就是开发样本的修复本身。当时的测试在默认 QEMU virt 上进行，那里 IPI 走 SBI，看不到这个告警。

### 3. lore 核对（`lore_check.md`）

第 2 条和第 12、13 条都没人报过。Mike Rapoport 正在审的 RFC（riscv set_memory 改用通用实现）也没有改 `__kernel_map_pages`。

### 4. 留出集检验（规则冻结后只跑一次，`ctxeval.py`、`heldout_eval.log`）

把本检查作为 CTX 引擎，在留出集的 76 个提交上做提交级比较：每个提交的前、后两个版本各跑一次静态检查，看子版本新出现的（钩子、架构、效果）。共 143 个版本，0 出错，有 3 个提交不改读取范围内的文件，走了快捷路径。

| 项 | 结果 |
|---|---|
| P5 正样本 47513f243b45（riscv 启用 KFENCE） | **判为可疑，对位成功**：新出现 riscv `kfence_protect_page` 的 IPI 候选（少数派）；后来的修复 b3431a8bb336 改的正是这个函数 |
| P5 正样本 a59e5468a921（arm64 poly1305） | 改动在 crypto 目录，不在读取范围内，没有覆盖 |
| 干净留出集召回（单独看 CTX） | 1/23，对位 1/23 |
| 48 个负样本的误报 | **0**（参考线：不超过 2 ✓） |
| **与之前五个引擎合起来**（干净留出集） | **召回 4 → 5，严格对位 3 → 4，误报 1 → 1** |

这是近几轮里第一次在干净留出集上拿到实打实的增量：47513f243b45 之前五个引擎都没抓到。

**需要如实说明的一点**：调试开发样本 fb1cf0878328 时，我看过它修复前版本上的全部候选，其中有一条是 riscv `kfence_protect_page` 的 X2。那次附带看到以后，没有针对它调整任何规则，修订 1 和它无关。

### 5. 新疑点的动态验证（`s8dyn_20261118`）

第 2 条（riscv `__kernel_map_pages`）在 QEMU 里做了动态验证。开 IMSIC、打开 `debug_pagealloc` 的 riscv 内核，9 次运行里 4 次 `kernel/smp.c` 告警、1 次卡死在 IPI 等待里，调用栈都是 `prep_new_page → __kernel_map_pages → flush_tlb_kernel_range → smp_call_function_many_cond`；四种对照（修复变异、关掉 debug_pagealloc、IPI 走 SBI、x86）合计 24 次，一次都没有。按事先判据，最后一轮 A 格是 2/3 加 1 次死锁，没达到 3/3，所以**没有判为确认**，详见那一轮的 README。

## 不足

1. 纯词法的区间识别，对“提前退出”“先解锁再调用”很敏感，修订 1 修好了一类，又引入了另一类误报（hugetlb）。更好的做法是按基本块和控制流来算。
2. 示例链常常不是真实路径；新疑点的成立，靠的是人工另找的真实路径。
3. 架构实现里的运行时条件（提前返回、`if (num_online_cpus() < 2)`、`riscv_use_sbi_for_rfence()`）都看不到。

## 下一步

1. riscv `__kernel_map_pages` 这个疑点是否报告上游（见 `s8dyn_20261118/README.md`）。
2. 区间识别改成按控制流计算，减少示例链不成立的误报。
3. 扩大调用上下文的覆盖面：架构内部的上下文问题，以及 crypto、驱动等目录。

## 文件

- 判据：`criteria.md`、`criteria_amendment1.md`、`criteria_sha256.txt`
- 分析器：`ctxeff.py`、`run.sh`；诊断：`debug_*.py`、`run_debug*.sh`
- 结果：`recall.json`、`recall.log`（`recall_run1.log` 是修订前的）、`head.json`、`head.log`（`head_run1.*` 是修订前的）
- 审查：`make_review.py`、`run_review.sh`、`review.txt`、`review.json`、`claude.json`、`codex_blind/`、`adjudication.json`、`lore_check.md`
- 留出集检验：`ctxeval.py`、`run_eval.sh`、`ctxeval_runall.log`、`heldout_eval.json`、`heldout_eval.log`
