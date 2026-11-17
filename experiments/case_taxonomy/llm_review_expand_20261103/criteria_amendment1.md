# 判据修订1：样本改为从LoongArch生成（实现之前写定）

## 为什么修订

按`criteria.md`第一节在RISC-V的20个快照上收集候选，结果见`candidates.json`：去掉以前复核过的之后**只剩4个**。原因是规则标出的位置在各版本之间基本不变，而v6.6、v6.12和终点版本上的标记前几轮已经全部用过。按第四节，a或b少于8个只作描述，所以在RISC-V上做不成。

用户选择**改用LoongArch生成样本**。RISC-V的4个候选不标注、不使用。

## 一、样本来源（替换原第一节）

**生成器**：`rules_la.py`。它是第2版规则（CTX、R7、R10），只把检查对象从RISC-V换成LoongArch，不改任何判断条件、正则或阈值。具体替换：

| 位置 | RISC-V（原） | LoongArch（本轮） |
| --- | --- | --- |
| 检查对象目录 | `arch/riscv` | `arch/loongarch` |
| 参照架构 | arm64、x86、LoongArch | arm64、x86、RISC-V |
| 陷入处理函数（CTX的B类） | `entry.S`中`excp_vect_table`列出的函数 | `genex.S`中`BUILD_HANDLER`生成的`do_<名字>`，加上`do_page_fault`（由`tlbex.S`调用）；不含中断入口`do_vint`，与RISC-V的做法一致 |
| R7的文件范围 | `kvm/`下全部，以及`kernel/`下ptrace、signal、sys_riscv、vector、compat_*、process | `kvm/`下全部，以及`kernel/`下ptrace、signal、syscall、process |
| R7常量下标排除的调用点范围 | `arch/riscv` | `arch/loongarch` |
| R10不计入的架构专用词 | 原列表 | 原列表加`riscv`、`sbi` |
| R10 Kconfig检查 | RISC-V的Kconfig | LoongArch的Kconfig |
| R10排除的自身前缀 | `riscv` | `loongarch` |

**等价性自测**（运行LoongArch之前）：把`rules_la.py`的检查对象设为RISC-V，在`v6.12`上运行。结果须与冻结的`rules_v2_unified_20261103/flags_dev_v6.12_run2.json`逐条一致，才说明移植没有改动规则本身。

**快照**：`v6.1`到`v7.2`全部正式版本，共21个。LoongArch的KVM从`v6.7`开始才有。

**去重与抽样**：同原第一节。键用`candidates.py`的`key()`；同一个键只保留最早的快照；多于60个时按种子`20261103`抽60个。LoongArch以前没有复核过，所以不排除任何键。

## 二、标签

同原第二节，终点版本仍为`df2908090cda`。

## 三、做法（相对原第三节的改动）

- **提示词措辞**：把`prompt()`中的“RISC-V”换成“LoongArch”。R10规则说明中的参照列表改为“arm64、x86、RISC-V”。其余文字不变。
- **不插入`facts.md`**：这份背景事实是RISC-V专用的，例如Svpbmt、RISC-V的陷入处理，对LoongArch不适用。也不另写LoongArch版，以免引入新的变量。
- **不变的部分**：
  - 声明格式`NEW_TAIL`、核对程序`factcheck.py`（不复制、不修改）、追问格式；
  - 每个问题3次，对照可选；
  - 模型、凭据、并行度、不重试、首批停止条件。

因此本轮检验的是复核做法的核心，即“写出可核对事实＋程序核对＋追问”，不含背景事实。

## 四、判定

同原第四节，成功标准与样本量下限都不变。

## 五、新增局限

- 规则是为RISC-V设计的，在LoongArch上标出的位置类型可能不同。本轮只用它生成样本，不评价规则本身在LoongArch上的效果；规则的标记数和真问题占比只作描述。
- 第一标注人对LoongArch代码的熟悉程度不如RISC-V，可能有更多c类（判断不了）。
