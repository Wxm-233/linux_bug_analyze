# M2b：检查族噪声收紧与主线结局标注（2026-10-28）

按用户“Register M2b”实施。登记`../registration_m2b.md`（SHA `580d5fd5…`）在实现与评估前写定，并如实列出写定前已知的信息（M2/M2a结果，以及上游`e795707703b3`对cluster属性的同类门控）。M2b = M2 ＋ M2a门控规则 ＋ F1b（只留`##`拼接实例）＋ F2b（上限宏展开链须含G本身）。**只说明实现与判别力，不说明泛化或精度。**不调用模型。

## 结果

| | die | shmem |
| --- | --- | --- |
| 实例（M2→M2b） | 10→10（全为拼接实例） | 18→3（去掉F1直接使用8个、F2无关配对7个） |
| 只在父版报 | 9格（`die_id`/`die_cpus`，同M2） | 1格（`HPAGE_PMD_ORDER`≤`MAX_PAGECACHE_ORDER`，arm64 64K） |
| 只在修复版报 | 0 | 0 |
| 两版都报 | 26格 | **0**（M2a为34格） |

事先预期全部成立：die不变；shmem去掉直接使用与`TASK_SIZE`配对后持续观察归零，目标保留。

## die持续观察的主线结局（v7.3-rc2，6个上下文构建全部成功）

| 结局 | 格数 | 内容 | 解释 |
| --- | ---: | --- | --- |
| 主线已解决 | 6 | `cluster_id`、`cluster_cpus`在s390、sparc64、x86无SMP | 与上游同日提交`e795707703b3`（cluster属性按架构支持门控）一致：后来被修掉的同类问题 |
| 主线仍存在 | 16 | arm64、riscv上cluster/core/package/thread各属性 | 这两个架构由`include/linux/arch_topology.h`提供这些宏；它不在`arch/`下，被“终态来自arch/才算原生”的判据误当作回退——是判据误报 |
| 主线仍存在 | 4 | x86无SMP的sibling/core掩码类属性 | 单CPU下`cpumask_of(cpu)`回退本身合理，上游长期接受 |
| 主线不可判 | 0 | | |

“主线已解决”不计独立正例（die已深度接触，且该提交与修复同属一个补丁系列）。

## 结论与下一步

- 收紧后两例信号都保留，shmem噪声归零；die剩下的26格中6格是后来被上游修掉的同类问题，其余20格分别源于“原生提供”判据的误分类（16）和合理的单CPU回退（4）。
- 下一步可登记M2c：把“原生提供”从“终态定义在`arch/`下”改为“终态定义不在消费者所依赖的公共`#ifndef`回退处”（使`arch_topology.h`等共享提供者算作提供），预期去掉arm64/riscv的16格；单CPU回退需另议。仍须先登记再验证。
- 两例已用于设计M2/M2a/M2b，后续真正的检验只能在未接触样本与正常对照上进行（重新冻结方法并经用户同意）。

## 实现与统计

`check_families.f1_instances(direct=False)`、`f2_instances(limit_contains_g=True)`（默认关，M2行为不变），测试`tests/test_check_families.py`共4项；执行脚本`../m2b_run.py instances/evaluate/mainline/label`；结果文件见`stats.json`所列SHA。WSL全量472项，仍只有原有2个pycparser导入错误。Kimi调用0次；新构建6次（主线die），M2b评估复用M2事实；0内核启动；新确认缺陷0；独立正例/正常0/0。本轮代码未提交（b708726之后）。
