# 判据修订 1（实现前，未看任何检查结果）

2026-11-08，Claude。原 `criteria.md`（SHA256 `f36af114…`）不变。下面五处是写判据时对内核宏展开的疏漏，在写分析器之前、没有运行任何检查之前修正。

1. **分析用的配置一律加 `CONFIG_DEBUG_ATOMIC_SLEEP=y`**，包括当前版本和样本的修复前/后版本。
   - 原因：没有这个选项时，`might_sleep()` 展开为空，内核中大量“此处可能睡眠”的标注在 AST 中完全不出现。
   - 这个选项只增加运行时检查，不改变被分析代码的锁与中断结构，属于静态分析的辅助输入。
   - 因此当前版本另建 `rv64_ctx` 配置（defconfig＋该选项），不用原 defconfig 构建。
2. **“可能睡眠”原语中的 `schedule*` 改为明确列表**：`schedule`、`schedule_timeout*`、`schedule_hrtimeout*`、`io_schedule*`、`schedule_preempt_disabled`。`schedule_work`、`schedule_delayed_work` 只排队、不睡眠，不算。
3. **trylock 不算可能睡眠**。`down_read*`、`down_write*`、`mutex_lock*` 系列中名字含 `trylock` 的排除。在锁原语中，trylock 按“可能+1”处理，与原判据一致。
4. **补充 `might_fault`、`__might_fault` 为可能睡眠种子**。`get_user`/`put_user` 是宏，展开后只剩 `might_fault()` 加汇编，不会出现名为 get_user 的调用。
5. **spinlock_t 的 irqsave 形式的识别**：`spin_lock_irqsave(lock, flags)` 是宏，展开为 `_raw_spin_lock_irqsave(spinlock_check(lock))`，名字与 raw 锁相同。
   - 规定：`_raw_spin_lock_irqsave`、`_raw_spin_lock_irqsave_nested` 的实参中出现 `spinlock_check` 调用时，按普通自旋锁（spin+1、irq+1）处理，否则按 raw 锁处理。
   - `_raw_read_lock*`、`_raw_write_lock*`（rwlock_t）按普通自旋锁处理，因为它们在 PREEMPT_RT 下同样会睡眠。

6. **分配函数的条件睡眠不经调用图传递**（第 1 条的直接后果）：
   - 开了 `DEBUG_ATOMIC_SLEEP` 后，`kmalloc` 等分配函数内部经 `might_alloc(gfp)` → `might_sleep_if(gfpflags_allow_blocking(gfp))` 调到 `__might_sleep`；按流不敏感的闭包，所有分配函数都会被算成可能睡眠，`GFP_ATOMIC` 的分配也不例外。
   - 原判据 3.2 的本意是只按调用点实参中的 GFP 常量判定，所以 `might_alloc` 作为被调者时不向上传递“可能睡眠”。分配调用只在实参文本含 `GFP_KERNEL`/`GFP_USER`/`GFP_KERNEL_ACCOUNT` 时，才在调用点算可能睡眠。

7. **spinlock_t 的 `_irq`/`_irqsave` 关中断单独计数**：
   - 状态由四元组改为五元组 `(irq, raw, spin, preempt, sirq)`，其中 sirq 是 spinlock_t 的 `_irq`/`_irqsave` 形式关闭的中断。
   - 原因：在 PREEMPT_RT 下，spinlock_t 本身就是可睡眠锁，`spin_lock_irqsave` 不关中断。在它的区间里再拿 spinlock_t，在 RT 下没有问题，不应报 R 类。在普通内核里，它确实关中断，所以 I 类（关中断时发 IPI 并等待）和 S 类仍然要算。
   - 规定：
     - **原子**：任一计数大于 0；
     - **I 类的“硬原子”**：irq、raw 或 sirq 大于 0；
     - **R 类的“硬原子”**：irq 或 raw 大于 0，不含 sirq。

以上七处都不涉及样本或结果，不改变评估方法、样本集与参考线。
