# 方法改动M2c：以“是否为公共回退定义”判原生提供（实现与评估前写定）

2026-10-28。用户批准“Register M2c”。基于M2b（`registration_m2b.md`）。**M2c在看过M2b主线标注之后写定，在die/shmem上的结果只说明实现与判别力，不说明泛化或精度。**

## 写定前已知的信息

M2b的die持续观察中，16格源于arm64/riscv的拓扑宏由`include/linux/arch_topology.h`提供（不在`arch/`下，在`#ifdef CONFIG_GENERIC_ARCH_TOPOLOGY`下无条件定义），被“终态来自arch/才算原生”误当作回退；`include/linux/topology.h`的回退形如`#ifndef M`紧接`#define M`。

## 改动（只改F1的“原生提供”与“可覆盖”判据）

- **回退定义**：宏M的某条`#define M`位于非生成文件中，且其之前至多3个非空行内有`#ifndef M`或`#if !defined(M)`（守卫的名字必须是M本身）。读取该文件在对应修订的源码判定；生成文件（如`include/generated/`）不算回退。
- **原生提供**`provided_M`：M在该上下文终态已定义，且终态定义不是回退定义。取代M2的`arch_provides_M`。
- **可覆盖宏**：在追踪上下文（x86_64/arm64/s390，同M2）中，至少一个上下文终态为回退定义、且至少一个上下文终态为非回退定义。取代M2“arch/与非arch/各有一个”的判据。
- F1b（只留拼接实例）、F2b、M2a门控规则不变；F2不涉及本判据，结果应与M2b相同。

M2c复用M2已采集的事实包（含终态定义文件与行号）及M2b的主线事实包，只新增“回退定义”标注，不新增构建；若出现M2未追踪宏的新实例，记为该实例事实不可得。

## 报告指标

同M2b：父版独有、修复版独有、两版都报（附主线结局）的观察格数，以及与M2b相比去掉/新增的实例。

事先预期：die中`physical_package_id`、`core_id`、`thread_siblings`、`core_cpus`、`core_siblings`、`package_cpus`在三个追踪上下文均为非回退，实例被去掉；保留`die_id`、`die_cpus`、`cluster_id`、`cluster_cpus`。父版独有仍为9格；两版都报约6格（cluster在s390、sparc64、x86无SMP），且应全部标“主线已解决”；arm64/riscv的16格与x86单CPU的4格消失。shmem不变（父版独有1格、两版都报0）。

## 不做

不调用模型；观察不称缺陷；“主线已解决”不计独立正例；是否进入冻结待用户确认。
