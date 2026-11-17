# 修订1（调试后写定，计算评估窗口结果之前）

**依据**：第2版规则在两个调试窗口上的第一遍结果（`flags_dev_v6.6_run1.json`、`flags_dev_v6.12_run1.json`）。

调试窗口`v6.6`中，A068（`arch_cpu_idle`应为不可插桩）没有被N1抓到。原因是：`v6.6`的`default_idle_call`并不直接调用`instrumentation_end()`，而是调用`__always_inline`的辅助函数`ct_cpuidle_enter()`，由它在内部调用`instrumentation_end()`；`ct_cpuidle_exit()`则在内部调用`instrumentation_begin()`。

**修改内容**：判断可插桩区间时（I1中的N1、N2），如果某个被调函数在索引中有定义，并且它的函数体中出现的最后一个可插桩区间操作是`instrumentation_end`（或`instrumentation_begin`），就把对这个函数的调用当作`instrumentation_end`（或`instrumentation_begin`）。只看一层。

**评估窗口**：`v6.1`的结果尚未计算。

**不变**：其余规则、评估方式、成功标准。

## 修订1b（评分程序的实现修正，同样在计算评估窗口之前）

**问题**：调试窗口`v6.6`中，`arch_cpu_idle`已被N1标出，但A068仍未算作命中。原因是：
- 修复改动的是函数签名那一行，即加上`noinstr`；
- 而评分时的函数范围从`{`所在行开始算，签名不在范围内。

**修改**：评分时，每个标记位置和调用链上函数的行范围都向上扩展4行，以包含函数签名。函数解析器取函数头时用的也是4行窗口。

**说明**：这只修正评分对“函数范围”的计算，规则本身不变。
