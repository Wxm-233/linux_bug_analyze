# 调用上下文检查（效果依赖版）：判据（写代码之前定下）

2026-11-18，Claude。用户：“做调用上下文检查”。

## 〇、和以前几轮的区别

以前的调用上下文检查有三轮：`ctx_rules_riscv_20261103`、`ctxcheck_dev_20261112`、`ctxcheck2_dev_20261112`。它们只看 riscv 自己内部的关中断区间和陷入入口，配合 PREEMPT_RT 做动态验证；样本不足，而且老内核编不过。

本轮放进“效果依赖”框架，按横纵两面来做：
- **横向**：同一个架构钩子，各架构的实现会不会“睡眠”、会不会“发 IPI 并等待”；
- **纵向**：公共代码有没有在不能睡眠或关中断的上下文里调到它。

架构内部、不经过公共接口的上下文问题（比如 LoongArch 在 CPU 启动时分配内存，88fd2b70120d）不在本轮范围内。

## 一、样本

| 用途 | 样本 | 说明 |
|---|---|---|
| 开发 | fb1cf0878328 | riscv `__kernel_map_pages` 经 `__set_memory` 拿 `init_mm` 的读写信号量，会睡眠；页分配器在原子上下文里调它 |
| 开发 | ce2b3a50ad92 | arm64 在 kfence、debug_pagealloc 的路径上，经 `split_kernel_leaf_mapping` 拿 mutex，会睡眠 |
| 检验（留出集，规则冻结后才看） | 留出正样本 47513f243b45（riscv 启用 KFENCE），修复是 b3431a8bb336 | 提交级：看引入提交是否判为可疑并对位 |
| 检验（留出集） | 留出正样本 a59e5468a921（arm64 poly1305，P5） | 同上，预计不覆盖 |

这两个开发样本来自对内核历史的关键词搜索（`irqs disabled`、`invalid context`、`atomic context` 等，只限 `arch/*/mm` 和相关头文件），搜索结果记录在 README 里。

## 二、横向：架构实现的上下文效果

1. **钩子**：在 `arch/<a>/include/asm/**/*.h` 或 `arch/<a>/mm/*.c` 里有定义（函数或函数式宏），并且在公共代码里有调用点。公共代码指 `mm/`、`kernel/`、`lib/`、`fs/` 下的 `.c`，以及 `include/linux/` 下的 `.h`。
2. **效果**：从架构 a 的实现开始，沿调用向下追最多 4 层。只追在 `arch/<a>/` 里有定义的函数和宏，以及 `include/linux/` 里的 `static inline` 函数。看是否到达下面的原语：
   - **睡眠**：`mutex_lock*`、`down`、`down_read*`、`down_write*`、`mmap_read_lock`、`mmap_write_lock`、`might_sleep`、`msleep`、`schedule`、`schedule_timeout*`、`wait_for_completion*`、`cond_resched`、`synchronize_rcu`、`stop_machine*`、`vmalloc`、`vzalloc`、`cpus_read_lock`、`flush_work`；另外，`kmalloc`、`kzalloc`、`kcalloc`、`alloc_pages*`、`__get_free_page*`、`get_zeroed_page` 的实参里含 `GFP_KERNEL` 也算。
   - **发 IPI 并等待**：`smp_call_function*`、`on_each_cpu*`、`stop_machine*`；另外，`sbi_remote_*` 也算（riscv 的远程刷新，同样不能在关中断时等待）。
3. 一个架构有多份定义（不同配置）时，任一份有某个效果，就算它有。

## 三、纵向：公共代码的调用上下文

1. **函数内区间**：在函数体的词法单元里，从“开始”到下一个对应的“结束”是一个区间。允许嵌套计数，函数结束时还没结束的就到函数末尾为止。

   | 类型 | 开始 | 结束 |
   |---|---|---|
   | 关中断 | `local_irq_disable`、`local_irq_save`；名字含 `spin_lock_irq`（包括 `_irqsave`）或 `lock_irqsave` 的调用 | 对应的 `enable`、`restore`、`unlock_irq*` |
   | 原子 | 名字含 `spin_lock`、`read_lock`、`write_lock`、`local_lock` 的调用（不含 `unlock`）；`preempt_disable`、`get_cpu`、`rcu_read_lock`、`local_bh_disable`、`pagefault_disable` | 对应的 `unlock`、`enable`、`put_cpu`、`rcu_read_unlock` |

   关中断区间同时也是原子区间。
2. **整个函数属于关中断上下文**：函数体以 `lockdep_assert_irqs_disabled()` 开头，或者含 `WARN_ON(!irqs_disabled())`、`VM_BUG_ON(!irqs_disabled())` 等写法。
3. **沿调用链传播**：函数 F 的某个调用点位于原子（或关中断）区间里，被调函数 G 就记为“可能在原子（或关中断）上下文中运行”，并向下传播，最多 4 层。只在公共代码的函数之间传播。
4. **钩子 I 的原子调用点**：公共代码里调用 I 的地方，要么本身在区间里，要么所在函数被记为“可能在原子上下文中运行”。保留一条示例链，方便审查。

## 四、规则

- **X1（会睡眠）**：钩子 I 有原子调用点，并且架构 a 的实现会睡眠，就报（I，a，睡眠，示例链）。
- **X2（关中断时发 IPI 等待）**：钩子 I 有关中断调用点，并且架构 a 的实现发 IPI 并等待，就报（I，a，IPI，示例链）。
- **少数派标记**：在实现了 I 的架构里，具有这个效果的架构不超过三分之一时，标“少数派”。少数派排在前面审查，这正是“只在部分架构上出错”的特征。不是少数派的候选也照样报出，但排在后面。

## 五、评估

1. **自测**：每条规则正反各至少 1 例。
2. **开发召回**：在修复前的版本上（fb1cf0878328^ 和 ce2b3a50ad92^）分别检查，期望报出：
   - fb1cf0878328^：（`__kernel_map_pages`，riscv，睡眠）；
   - ce2b3a50ad92^：arm64 的 `kfence_protect_page`、`__kernel_map_pages`、`set_direct_map_*` 三者中任一，效果为睡眠。

   参考线：2/2。
3. **当前版本（df2908090cda）**：报告候选数和少数派数。少数派全审，不超过 40 条；如果超过，取前 40 条。我和 Codex 盲判，然后裁定。
4. **检验（规则冻结以后，只算一次）**：
   - 把本检查作为引擎 CTX，在留出集的 76 个提交上跑提交级比较：签名为（钩子，架构，效果），只报子版本新出现的；
   - 报告两个 P5 正样本是否判为可疑、是否对位（用 archsig 的 Fixes 反查对位）；
   - 报告 48 个负样本的误报数。
   - 参考线：误报不超过 2 个；召回如实报告。
