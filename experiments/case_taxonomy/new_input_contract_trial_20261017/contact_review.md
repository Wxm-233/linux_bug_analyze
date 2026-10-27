# N2.6 选例前接触审计与固定选例（2026-10-17）

本轮沿用 `core_consumer_qualification_20261017` 已冻结的 500 条 Git 元数据、两队列、路径优先级及种子 `N1-core-common-consumer-20261017-v1`。脚本 `select_metadata_cases.py` 独立重算原两队列排序并与旧 `selection.json` 的完整顺序逐项相等后，才减去以下明确接触项；未用标题、层级、旧模型标签或缺陷结论参与排序。新 `selection.json` 首次生成后采用独占写入，后续不能重排、补选或替换。

| 排除身份 | 选前接触依据 | 处理 |
| --- | --- | --- |
| `ba831b7b1a517ba7f25d6fa9736a8092d07b0c74`（原 C） | `core_parent_analysis_20261017/protocol_pre.json` 登记 C 的父版源码与后续选中修复材料审查。 | 首队列明确排除。 |
| `bfcc4397435dc0407099b9a805391abc05c2313b`（原 D） | 同一协议登记 D 的父版源码与后续选中修复材料审查。 | 次队列明确排除。 |
| `bb7a5e44fc6f3d5a252d95c48d057d5beccb8b35` | 旧 `exposure_index.json` 仅标成研究笔记接触深度待核；选前进一步查看 `temporal_rule_v2_review.md:11`，其内容明确讨论目标 `kernel/sched/topology.c` 补丁和 `claim_allocations()` 等函数。 | 作为已有目标补丁／函数级接触排除；不采用该行的旧评价。 |

查找接触路径时，`temporal_rule_v2_review.md:11` 的旧评价文字曾**非预期可见**。本轮只提取其“此前讨论过目标补丁和函数”的接触事实，没有采用相关／不相关、正／正常或机制判断。此前对带协议、选择、元数据、暴露命名文件和少量命名研究笔记进行过有界 hash 命中扫描；这些扫描没有打开原始模型回答或新提交正文，但不能证明全局未接触。随后按主流程限定，只以旧 `exposure_index.json`、本日 C/D 协议及明确接触行作为本次排除依据。旧索引中其他“笔记引用、接触深度未知”的条目仍保留其未知状态，单纯列名或 hash 命中不算源码阅读。

固定结果为 E=`7a4dcb4a5de1214c4a59448a759e2e264c2c4473`，精确单父版 `6eaae198076080886b9e7d57f4ae06fa782f90ef`，队列 `public_preparation_lifecycle`，命中 `kernel/cpu.c`；F=`9942cb22ea458c34fa17b73d143ea32d4df1caca`，精确单父版 `d2e9f53ac5dd76dadc0b5f04f6c27640604ce2af`，队列 `public_topology_interface`，命中 `drivers/base/arch_topology.c`、`include/linux/arch_topology.h`、`include/linux/sched/topology.h`。完整剩余顺序与路径、优先级、rank SHA 保存在 `selection.json`：首队列剩 6 项、次队列剩 7 项，每队列仅取 1 项。

按原路径规则给 E 规划 `kernel/cpu.c` 与 `include/linux/{cpu,cpuhotplug}.h`，给 F 规划 `drivers/base/arch_topology.c` 与 `include/linux/{arch_topology,sched/topology}.h`；这些是待按精确父版收集的路径计划，不证明文件存在、消费者完整或案例合格。E 的公共路径与旧 C 重叠，F 的公共路径与旧 D 重叠；路径相同不证明同修复家族，也不证明目标函数从未被读过。两项的旧索引均为 `not_found_in_scanned_records`、家族未知，须在选中后对实际文件／函数范围做有限接触比较。全 500 条均已有 DeepSeek 初筛接触，因此两项都不能称全球模型未见或独立阳性／正常。此阶段未读 E/F 新父版正文、child 消息或补丁，未进行新模型调用。
