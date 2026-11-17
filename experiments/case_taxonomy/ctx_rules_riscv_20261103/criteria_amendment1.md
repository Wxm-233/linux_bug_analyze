# 修订1（调试后写定，计算测试集结果之前）

**依据**：第一遍运行（`flags_run1.json`）中，开发正例的命中情况，以及去掉测试正例相关函数之后剩下的41个标记（`tune_view.py`）。测试集结果尚未计算。

**修改内容**：

a. **跨核调用只在“硬”原子上下文中算作违规。**
- 涉及的函数：`on_each_cpu*`、`smp_call_function*`；
- “硬”原子上下文：关中断区间、raw自旋锁区间、陷入入口，以及来自这两种区间的跨核回调与钩子；
- 依据：内核要求这类调用不能在关中断时进行，但持有自旋锁或禁抢占时调用是允许的。第一遍中由此造成的误报，例如持页表锁时刷TLB，占大多数。

b. **标了`__init`的函数中的区间，不作为原子上下文的来源。**
- 依据：判据第五节已把早期启动排除在外，而`start_kernel`的关中断区间覆盖了整个早期启动过程，例如`setup_arch`、`init_IRQ`、`time_init`。

c. **不沿入口框架函数往下查**：`irqentry_*`、`syscall_enter_from_user_mode*`、`syscall_exit_to_user_mode*`、`exit_to_user_mode*`。
- 依据：这些函数自己管理中断状态，例如`irqentry_exit_to_user_mode`会先开中断再调度。

d. **忽略`mm/highmem.c`中的定义。**
- 依据：RISC-V不支持HIGHMEM，`page_address`在RISC-V上是宏。

e. **名字中含`for_each`的不当作函数。**
- 依据：这是解析造成的误识别，例如`list_for_each_entry`。

f. **N1规则加上跨架构证据。** 只有当arm64、x86、LoongArch中至少一个同名定义标了`noinstr`、`__cpuidle`或`__always_inline`时，才标记RISC-V的版本。
- 依据：判据要求的是跨架构缺陷，参照架构的标注说明“这里需要不可插桩”是这条约定的一部分。

g. **跨核回调的识别，按“参数是RISC-V定义的函数名”取。**
- 依据：判据写的是“第一个参数”，但`on_each_cpu_mask`、`smp_call_function_single`、`stop_one_cpu`的回调都不是第一个参数。这里是按判据的本意改正写法错误。

h. **同一函数、同一行、同一种类的标记，不论来源，只保留一个。**

**不变**：调用链深度3、K1清单、K3规则、成功标准、评估方式。
