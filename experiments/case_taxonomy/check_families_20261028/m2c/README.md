# M2c：以“是否为公共回退定义”判原生提供（2026-10-28）

按用户“Register M2c”实施。登记`../registration_m2c.md`（SHA `e402bd39…`）在实现与评估前写定，并列出写定前已知的M2b主线标注结果。**M2c在看过M2b之后写定，在die/shmem上的结果只说明实现与判别力，不说明泛化或精度。**不调用模型，不新增构建。

## 改动

F1的“原生提供”从“终态定义在`arch/`下”改为“终态定义不是回退定义”：`#define M`之前至多3个非空行内有`#ifndef M`或`#if !defined(M)`（守卫须是M本身）即为回退，生成文件不算。“可覆盖宏”相应改为：追踪上下文中至少一处终态为回退、至少一处为非回退。F1b、F2b、M2a门控不变。

实现：`kernel_facts.is_fallback_definition`、`annotate_fallbacks`（`collect`此后也自动标注）、查询`macro_provided`；`check_families.f1_instances(provided="fallback")`。M2c在内存中为M2已有事实包与M2b主线事实包补标注，不改写任何已有证据文件。测试`tests/test_check_families.py`新增1项（共5项）；WSL全量473项，仍只有原有2个pycparser导入错误。

## 结果（与事先预期逐项一致）

| | M2b | M2c |
| --- | --- | --- |
| die实例 | 10 | **4**（`die_id`、`die_cpus`、`cluster_id`、`cluster_cpus`；其余6个在三个追踪上下文都是非回退，去掉） |
| die只在父版报 | 9格 | **9格**（同一组die信号） |
| die只在修复版报 | 0 | 0 |
| die两版都报 | 26格（6已解决、16判据误分类、4单CPU回退） | **6格，全部“主线已解决”**（cluster在s390、sparc64、x86无SMP） |
| shmem | 父版独有1格、两版都报0 | 不变 |

M2c下die剩余的每条观察，要么是本次修复的缺陷，要么是上游同系列提交`e795707703b3`后来修掉的同类问题；arm64/riscv由`include/linux/arch_topology.h`提供的16格与x86单CPU的4格不再生成（后者是因为追踪上下文x86_64 defconfig为SMP，相关宏在那里非回退，实例不成立——这也意味着只在非默认配置出现回退的情形会被漏掉）。

## 边界与下一步

- M2/M2a/M2b/M2c都是在这两例上调出来的：die与shmem已不能再作证据，只能作回归用例。
- 实例由三个追踪上下文（x86_64/arm64/s390 defconfig）决定，只在其他配置出现回退的宏不会成为实例。
- “主线已解决”6格不计独立正例（同一补丁系列）。
- 下一步：重新冻结方法（检查族M2c＋事实工具，die/shmem作回归），经用户同意后在未接触样本与正常对照上评价命中与误报；只用检查族可不调用模型。

## 统计

Kimi调用0次；新构建0次；0内核启动；新确认缺陷0；独立正例/正常0/0。结果文件与SHA见`stats.json`。本轮代码未提交（b708726之后）。
