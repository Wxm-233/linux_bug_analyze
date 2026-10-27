# N2.12 冻结后结果归属复核（2026-10-18）

方法基线 `method_baseline.json` 已在实际结果前冻结；原 `program_results.json`、`source_check_results.json` 保留未改。两个已读 GIMPLE 片段均返回 `partial_local_facts`：s390 为 179 个事件、37 条局部依赖，x86 为 182 个事件、37 条局部依赖。参考检查是另一助手对既有源码的有限人工释义，不是未见 Linux 样本或专家真值。原冻结比较结果为 20 问中 2 `match`、2 `mismatch`、16 `insufficient`，不能把 `mismatch` 直接解释成两个错误源码事实，也不能把 `insufficient` 算正确。

直接核对原片段和程序原始事件：每版确有 3 条 `rq->core` 读取（程序 `kind=load`、`field=core`）和 1 条 `rq->core = core_rq` 写入（`kind=store`、`field=core`）。s390 源片段第 107/108、182/183 行分别呈现 `_16 = rq->core`→`if (rq == _16)`、`_29 = rq->core`→`_30 = core_rq != _29`；程序对应 E88→E89（region 77）和 E149→E150（region 141）都有精确 `_16`/`_29` 依赖边。x86 对应第 110/111、188/189 行，程序 E89→E90（region 79）和 E151→E152（region 145）也有边。这证明有限的原文对接和局部语法关系；未证明调用语义、相同指针对象、全局到达定义或接口要求。

原比较器不识别参考词汇 `field_load`、`field_store`、`condition`、`assignment`，而程序公开词汇为 `load`、`store`、`branch`、`scalar_assign`。因此两个 F02 的 `actual.count=0` 是选择器词汇未对接；原程序已有各 1 个真实 `store`，不能据此说方法漏掉写入。F05/F07/F08/F09 的大部分 `insufficient` 也先停在锚点词汇门槛，不能先归因于依赖算法失败。全局计数 F01/F03/F04/F10 被相关 opaque E16 `void unlock = <<< error >>>;` 保守牵连，尽管明确的三次 load 和十二次 call 等事件在原 packet 中可见；这说明比较器覆盖策略过宽，不证明这些事件为假，也不能未经新协议就把 zero count 直接转成成功。

若继续做词汇接线，只能作为**检查预期已揭示之后**的另行登记工程回放：固定原 `program_results.json` 和原参考不改，以明确有限映射再运行并另存结果；原 2/2/16 成绩必须完整并列。即使接线后更多问能对上，也只是已读源码的接口兼容/忠实度开发回放，不能追认为原冻结成绩、独立泛化或自动推导跨架构契约的提升。`condition` 在本参考的两项是显示分支；以后不应无条件假定所有 condition 都对应 `branch`。
