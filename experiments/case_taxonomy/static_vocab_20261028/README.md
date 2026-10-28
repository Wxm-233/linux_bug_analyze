# 静态事实词表扩展：读写端点、初始化阶段、调用可达

2026-10-28。设计见[design.md](design.md)。试点均为已接触、不计评价的后备池提交。

## 实现

- `kernel_facts`：按预处理行标记为本源文件函数建索引（段属性、语法读/写/取地址/调用、initcall对应），新增查询`writes`、`reads`、`escapes`、`in_init`、`initcall_level`、`calls`、`reachable`、`writers_count`、`all_writers_in_init`、`any_reader_outside_init`，以及恒定值`constant`。
- `candidate_bridge`：对每个角色函数加`in_init`，对被引用行的对象加读写与写入者集合，对提供者/消费者间加双向`reachable`；词表加恒真配置事实`build_context`；形式化提示新增`necessary`模式（允许只写要求的非平凡必要条件，标`strength`）。
- `bridge_run.py`：通用`prepare`（WSL：查询→事实包→回答→值盲提示）与`evaluate`（校验、未审/审后判定；研究者复核可附规范化形式）。

## 开发回归（SPARC，与源码对照）

`writes(record_one_cpu|of_populate_present_mask, ncpus_probed)`为真；`reads(record_one_cpu, nr_cpu_ids)`修复版真、父版假（对应修复新增守卫）；`reachable(setup_arch→smp_fill_in_cpu_possible_map)`父版真、修复版假（修复删除该调用）；`in_init`：setup_arch/alloc_irqstack_bootmem真、record_one_cpu假。已知局限：回调参数（`of_iterate_over_cpus(record_one_cpu, …)`）不进调用图；这些文件无initcall，`initcall_level`未得到验证。SPARC通用位宽回归仍4/4。

## 试点结果

| 试点 | 查询 | 回答 | 严格形式化 | 必要条件形式化 |
| --- | ---: | ---: | --- | --- |
| 试点2（amd.c，5候选） | 191 | 175 | 0/5可表达（扩展前同为0/5） | 1/5写出，但scope为字面true被校验拒绝 |
| 试点3（mm/madvise.c，2候选） | 28 | 23 | 0/2 | 0/2 |

- 试点3选取首次命中一个只改非C文件的提交（A0通过但无E1输入），保留为`pilot3_selection_attempt1_no_c_sources.json`，试点改取下一个触及C/头文件者。**正式评价中此类样本只能记“E1不适用”**；若要把“触及C/头文件”加入A0判据须另立协议附录。
- 研究者复核（`researcher_review_sv_pilot2_necessary.json`）：试点2候选3的“提供者不在init段”是与“热插拔/resume后需重新同步每CPU缓存”相关的弱必要条件；把字面`true`规范化为`build_context`后审后判定**满足**（`provider_in_init`为假）。这是链路首次走到审后判定；满足不证明要求成立。审前原结果保存为`sv_pilot2_necessary_results_before_review.json`。

## 不可表达理由（导出于`sv_pilot2_reasons.txt`、`formalization_review_notes.txt`）

- 试点2：仍缺实际数值（核心数/位宽/MSR值）、跨事件时序（BSP初始化 vs 外部查询、热插拔/resume）与位域语义——静态读写/可达只覆盖了“谁写谁读”。
- 试点3：两个候选都是**跨架构宏可见性与取值**（`MADV_*`在各架构UAPI头中是否定义、值是否与ABI一致；`CONFIG_MEMORY_FAILURE`下Alpha/Xtensa/MIPS是否提供`MADV_HWPOISON`/`MADV_SOFT_OFFLINE`）。这类要求可由“各架构配置下宏是否定义/取值”的编译期事实表达，但当前词表没有宏事实，也没有跨架构维度。

## 结论与下一步

静态读写/阶段/可达事实可普遍取得（试点2 175/191），但对真实候选的表达贡献很小（严格0/7；必要条件1/7，且需研究者规范化）。试点3表明最直接的下一步是**宏事实+跨架构采集**（同一文件在多个架构配置下预处理，查询宏是否定义、取值，并做架构间对比）——这正是E3所需维度，也与项目的跨架构主线一致。数值/时序类要求仍需运行时观测或改变E1表述。

## 统计

6次Kimi调用（试点2严格/必要条件形式化各1、试点3 E1/严格/必要条件各1，均完整交付；另试点3首选未调用），3个事实包（SPARC 2个、x86_64 2个中1个复用）；新确认缺陷0，独立正例/正常0/0。评价方法冻结仍过期；代码未提交。
