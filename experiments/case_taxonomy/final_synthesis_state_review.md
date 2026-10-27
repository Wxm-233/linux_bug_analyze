# 最终总结前的状态/能力路线：固定元数据池未找到独立同机制留出

日期：2026-09-28。此轮按照[四类条件契约底稿](final_summary_pattern_contracts.md)的 P3/P4 和 W3 有界预案，优先尝试现有 topology v3 的**能力导出**机制：通用 sysfs 属性只有在目标版本/配置确有原生 ID 与 CPU-map 提供者、且构建和注册链可达时才应向外可见。目标是找未读源码、未参与 die/cluster/book/drawer 规则开发的同机制修订，并同时预留一个正常对照。**结果是在限定元数据池中未找到合适阳性，因此停在事前选样，没有运行新样本，也没有任何 hit/normal 等分类。**这不是规则的阴性测试，更不是零漏报证明。

## 事前选样范围和排除依据

只读两种元数据：`analysis_out/stratified-20260921/manifest.json` 的固定 500 个 SHA/标题，以及本地 `/root/repos/linux` 中 `drivers/base/topology.c` 的 `git log --all --no-merges --format=%H%x09%cs%x09%s -- drivers/base/topology.c`。未读取本轮潜在目标的提交正文、补丁或历史源码。固定 500 清单 SHA-256 为 `8e61c456af84b1cee027a38793e4146a5d96bf652307fc83582e4c661f4d995a`；以宽松标题表达式 `topolog|sysfs|die|cluster|book|drawer` 找到 **47/500** 条，但这只是检索命中，包含许多 CPU 解析、设备拓扑、普通 sysfs 和标题中的偶然字符串，并非 47 条同机制提交。

本地 `drivers/base/topology.c` 的非合并历史为 **54** 条；与固定 500 的 SHA 交集只有两条：`2c4dcd7fd57b` 是**已读** die 导出修复；`6bceea7a1e07` 标题为 `arch_topology: Relocate cpu_scale to topology.[h|c]`，仅从标题不能合理预期它是“book/drawer 属性错误导出、缺原生提供者”的同形阳性。旧版 book/drawer 的 `f1045056`、`a62247e1`、`b40d8ed4` 都已经用于 v3 开发；同一路径的 die/cluster 修复 `2c4dcd7f`、`e7957077` 也已用于先前校准。PPIN 是运行时单值能力可见性，既有报告明确将其列为不同接口形状，不能硬塞进 book/drawer 双提供者规则。[具体池、交集、排除记录](final_synthesis_state_prescreen.json)单独保存，避免把“没找到”说成遍历 Linux 所有接口后的结论。

冻结前已有 v3 脚本 `topology_v3_versioned.py` SHA-256 `72889e2c9bfa1bf716c44ba0141c2b9ea663d3f4c486989847ab4be1d6b5ae5c`；代码本身明确只支持 s390/x86 的 **book/drawer** 家族，已读开发网格的 4 normal/6 insufficient/14 not applicable 不是新留出结果。[v3 开发记录](topology_v3_development.md)还说明历史 Kconfig 和属性模板的版本差异曾使 v2 留出出现 runner_error。因此即使让 v3 对固定 500 中其他“topology”标题运行，也只能得到范围拒判或不相干配置记录，不能检验同机制检出。规则没有足够的未读、独立、可合理预期同形阳性，所以**不再读新补丁、不冻结空的旧版/配置网格、不运行正常对照，也不重复换样**。状态就绪的旧探针同样依赖人工预标 P/C，没有现成可对未知接口直接运行的通用提取器；这次不临时写一个未校准的新规则来凑 W3 阳性。

| 要报告的运行分类 | 本轮结果 | 正确解释 |
|---|---|---|
| `hit` / `normal` / `not_applicable` / `insufficient` / `runner_error` | **全部未测量** | 选样门槛未过，没有原始运行输出；不能把“无适合目标”记作五类中的任何一类，也不能算准确率。 |
| 独立同机制目标 / 正常对照 | **0 / 0 个选定** | 事前检索没有可合理预期的同形阳性，因此按 W3 上限停机；并非证明数据库内没有其他此类问题。 |
| 本轮付费模型调用 / 补丁或源码解封 | **0 / 0** | 限于本地清单、Git 标题/日期/路径和已存在的规则定义。 |

后续若要真正检验 P4，需先找到**另一接口家族**但具有“公共导出—原生提供者—fallback—可达配置”完整形状的未读修订，并在读源码前冻结候选规则、旧版、配置和正常对照；现有 v3 需要扩展到那个接口，扩展所用样本只能算开发集，再取另一个新留出。若目标改成 P3，则应先实现能从单旧版源码提取同一状态 P/C 和条件 A 的受限候选器。当前结果如实说明 P4 的**开发回放已存在，独立跨家族验证仍缺**；可直接作为最终 Word 的方法限制，不阻止形成有界的初步总结。
