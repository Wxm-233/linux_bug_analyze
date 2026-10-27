# Topology sysfs 来源提取：已读案例校准

日期：2026-09-26。本轮是对[两个研究问题的路线](teacher_questions_roadmap.md)中“自动提取候选事实”所做的**受限实现**。[`topology_contract_extract.py`](topology_contract_extract.py) 从指定历史 Linux Git 版本读取 `drivers/base/topology.c`、拓扑头、架构头、Kconfig、Makefile 与 asm-generic 映射，追踪 die/cluster 三项 sysfs 属性的 show/read 定义、数组注册、原生 ID/CPU-map 宏和通用 fallback 的先后。它输出与冻结 C 规则兼容的事实、逐项源码行号和未知原因，再由 [`contract_check_pilot_v1.py`](contract_check_pilot_v1.py) 计算 `hit/normal/not_applicable/insufficient`。**它不推断未知接口的正确 ABI 或硬件含义。**

脚本最终 SHA-256 为 `4eda43ceccd1bfd6b6a1ed1c1d42aab6f8d200908bc9787c7859544d27cf714a`；本轮使用的 die/cluster 都在编写脚本前已读过，故下面只是**校准**，不是独立留出。完整逐项事实、源码位置与脚本哈希在 [`topology_contract_extract_known_result.json`](topology_contract_extract_known_result.json)。

| 已读校准记录 | 条数 | 检查意义 |
|---|---:|---|
| `hit` | 4 | die 旧版 s390/ARM64 与 cluster 旧版 s390/x86 非 SMP：历史源码导出属性，但该配置下缺两项原生提供者。 |
| `normal` | 12 | 有原生提供者时保留导出，或修复版对缺提供者的配置隐藏属性。 |
| `insufficient` | 1 | PPIN 属运行时单值可见性，不符合静态 ID+CPU-map 双提供者规则。 |
| `not_applicable` | 1 | `CONFIG_SYSFS=n`，目标接口未构建。 |

这 **18 条是版本×架构/配置×接口的记录**，不是 18 个独立缺陷，也不能据此计算精确率、召回率或提速。提取器将 RISC-V 的 `asm/topology.h` 明确追到 `include/asm-generic/Kbuild` 映射；若映射不存在或不认识，就输出证据不足，而非把缺少专用头文件当成缺能力。测试先发现并修正了四种潜在的虚假确定性：被条件关闭的 `#include`、未知 Kconfig 外层条件、条件构建的 `topology.o`、宏定义后又被 `#undef`；另核查未知导出守卫与读取函数条件。`tests/test_topology_contract_extract.py` 共 12 项通过，18 条真实历史源码校准与已有人工矩阵相符。这里的测试是受限解析边界与已读回归，不是历史内核启动或新样本盲测。

当前回答老师第一问仍是**部分进展**：这类历史 topology 接口的来源事实已能由程序从源码提出，减少了手工逐行抄录；但接口家族范围是人为指定的，Kconfig/预处理只支持明确列出的简单形状，运行时能力、跨函数状态时序、硬件规范和未知子系统仍需其他提取方式。第二问也仍未通用解决：输出标记为 `implementation_contract_candidate`，表示源码中的消费者—提供者和 fallback 关系，**不等于**外部 ABI、真实设备拓扑值或领域认可的权威契约。出现版本/架构/模式冲突时，按路线文档保存双方证据并请求领域裁定，检查器保持 `insufficient`。

下一步在新样本**阅读补丁前**冻结提取器与选择池快照、脚本哈希、判准和计时方法。topology 专用解析器只能在相同接口形状上验证提取稳定性；若要检验“跨架构机制提炼”的独立根因迁移，应先为另一类接口定义自己的来源/消费者证据，再取不同子系统样本，不把新的运行配置当成独立案例。发现时间与五维分类的缺口仍按当前代办并行处理。
