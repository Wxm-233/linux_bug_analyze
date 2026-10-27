# 两个核心方向：首轮最小契约协议

2026-10-16。用户已确认以N1“自动推导跨架构接口要求”和N2“契约驱动的跨架构对照检查”为两个核心研究方向。**方向已选定，新意与有效性尚待证明。** 本轮完成N1的协议／执行基础和有限选例资格审计；没有实现通用C提取或N2自动选配置。

## 本轮解决什么

旧卡把具体架构、配置、函数和成员关系放在判定器中。现在分为：

1. **契约候选**：声明适用条件、关系表达式、类型与各字段来源。
2. **外部审核账本和适配器**：独立登记规范／用途依据、提供者、对象、实际消费期限、配置与观测事实。模型不能通过自己标记“已审核”直接获得采用资格。
3. **纯判定核心**：只计算支持的关系、核对输入是否与已审条件相符。核心不内置架构、函数、CPU编号、self关系、修订号或old/fixed标签。

代码：[contract_protocol.py](../../../linux_bug_analyze/contract_protocol.py)。测试：[test_contract_protocol.py](../../../tests/test_contract_protocol.py)。案例适配：[replay_known.py](replay_known.py)。结果：[results.json](results.json)。

**这一步是把已知检查整理成可复用基础，不是已经自动提取契约，更不是已经发现新问题。** 语义审核和案例映射仍由研究者提供，必须单独统计人工介入。

## v1协议边界

调用为 `evaluate_contract(contract, ledger, record, allow_synthetic=False)`。三个参数是分离输入；审核账本不得由模型回答中的自评字段直接生成。`results.json`保存一份完整的已读契约实例；适配脚本可重建账本与输入，不重复归档旧源码。

| 输入 | 最小内容及约束 |
| --- | --- |
| contract | schema、id、历史revision、authority_kind、非充分性标志、field_origins、required_claims、symbols、scope与relation AST |
| required_claims | authority、interface、consumer_requirement、provider_binding、object_binding、deadline_binding、applicability七种角色，分别引用外部审核记录 |
| authority_kind | documented或consumer_inferred。后者只是经复核的条件性用途要求，不能自动升级为书面规范或据此认定错误产生侧 |
| symbols | bool、int、string或有限int_set；角色为configuration或observation。适用条件只读取明确的配置／路径事实，不从架构名字猜值 |
| ledger | 绑定contract_id、revision、field_origins、context_id和basis；包含独立审核claims与文档范围索引 |
| claim | role、status、origin、statement、context_id及references。配置/关系AST、符号、权威类别、对象和期限须与所批准内容精确匹配，不允许借用另一检查的审核 |
| document | path、context_revision、start_line、end_line。context_revision表示适用于所查源码版本；文献自身版本与适用语义仍须审核，不由引用行号认证 |
| record | id、revision、context_id、basis、object_id、sample_event、sample_kind、deadline_event、observation_binding、facts |
| fact | value、claim；观测事实另含object_id和event_id。外部fact记录同时绑定类型化值、符号、配置／运行context及必要的对象／事件 |

支持 `contains/nonempty/eq/ne/lt/le/gt/ge/and/or/not`，表达式限制深度8、节点64。不会执行任意Python/C代码，不推测未知时序。`precedes`等尚无真实事件适配的关系拒绝求值；不能用字段齐全代替机制证据。

关键约束：

- **规范与消费者要求分开。** 当前消费者可能包含错误假设；规范冲突或不明时输出不足，不自动指责架构提供者。修复新增政策不可据此追溯为旧版已有规范。
- **合法条件与未知分开。** 缺配置不等于关闭；明确的所选路径条件为false才报告本契约不适用，且不认证回退路径正常。
- **对象和运行上下文分开。** 相同变量名不足以建立同对象关系；提供、消费、期限和观测须绑定同一对象及配置／运行context。
- **采样和内容消费分开。** 提前采样只能报告采样处关系；不能靠修改事件名称或取得指针来升级为内容消费。v1没有采样到期限的稳定性桥接。
- **来源和证据层级分开。** 模型／程序／研究者字段来源与synthetic/source_projection/archived_runtime层级分别记录。synthetic必须显式启用，且不能改名成真实运行。
- **谓词原样计算。** 不把nonempty偷偷增强为contains，也不以无WARN作为正确性依据。Python布尔和整数不能借`True == 1`互换审核值。

输出包括 `applicability`、`relation_at_observation`、`relation_at_deadline`与`whole_path`。关系为satisfied、violated、not_applicable、insufficient四态；适用性明确成立时为conditional_applicable。即使窄关系满足，whole_path始终不足。源码投影仍是源码投影，精确事件的逻辑结论也不自动变成真实运行复现。

## 验证与发现的边界

本轮28项新离线测试覆盖关系参数化、合法条件／未知、同对象／同context、事件身份、外部审核与模型自批准、精确类型、依据冲突及分层输出。旧卡25项回归通过。测试数量不是缺陷数量，也不构成泛化准确率。

适配程序仅回放10/15已记录的五个构造输入：窄成员关系为2项违反、3项满足，与旧卡一致；五项消费期限与整体正确性全部保持不足。没有新C执行、历史内核启动、模型请求或确认缺陷。程序测试里的标量／集合变体只检验参数化能力，不能算新的跨架构样本。

独立复核在初版发现并复现了三类问题：借用已审核AST、语义claim混用对象／context、Python bool/int等值误匹配。已据此增加精确审核绑定、对象／context核对与类型严格比较；旧失败意见保留为本节记录，不称一次写对。

`results.json.version_files`只记录本轮三个执行／测试文件版本，供后续解封前固定方法；未做全项目递归封存。本轮不得用新样本结果回改协议后仍将该样本称为原冻结方法的独立检验。

## 独立样本资格复核

沿用旧[两条预备近邻](../state_contract_refine_20261015/selection_next.md)。本轮只读固定标题、运行身份／状态、账本元数据和已有阅读记录；未读新增提交说明、源码、diff、assessment或响应正文。

| 预备项 | 新核实的接触状态 | 资格仍缺什么 |
| --- | --- | --- |
| `7202e979645715318f2f21a324cb8a506e12fa76`，C-SKY hotplug同步迁移 | 已进入DeepSeek-V4.1-Flash旧初筛但失败；failed_review[10]、两个运行账本及原始响应路径有记录。不能把跨账本条目简单加总为新请求 | 主分析／规则开发接触未证实；同机制、真实缺陷与家族独立性未确认 |
| `f1c6b957f7f4091d822b93ca2833e83bf728e001`，sched拓扑条件编译标记整理 | 同模型旧初筛status=success；没有阅读其判断正文 | 不能根据标题认定正常；需确认同用途消费路径与行为不变，且排查开发材料重叠 |

固定500另有 `2711b8e2b71fa3cce9c28b0f07b75882f141adfe`，标题为x86 hotplug同步迁移，是C-SKY项的家族审查线索。协议完成后又读取这三项的日期、父提交和变动文件名，保存为[资格元数据](qualification_metadata.json)：C-SKY与x86两项分别于2023-05-15相隔2秒提交、作者时间相隔6秒，均改Kconfig／smp头和启动实现，支持“可能属于同轮迁移”的审查线索，仍不据此确认系列或真实缺陷。标记整理项为2025-06-13提交、仅改kernel/sched/topology.c；它与当前已读5.14消费者不是同版本，不能直接作同接口正常对照。没有读取提交说明正文或diff。

两条初筛接触不自动排除“未用于规则开发”的资格，但不能称完全未读；固定分层样本也不能当总体等比例随机样本。

审计入口为 `analysis_out/stratified-20260921/manifest.json`、`identity.json`、`results/f1c6b957f7f4091d822b93ca2833e83bf728e001.json`、`failed_review.json`和`runs/1789955802711625056/usage.json`、`runs/1789955957813661906/usage.json`。这些是既有被忽略数据，不复制进本目录。

**正式独立同机制正例0、同接口正常对照0。** 当前进步是纠正接触状态与完成协议基础，未完成独立检出。

## 下一步与N2的输入

下一项沿冻结版本先对预备近邻做资格审查：核对共同迁移系列、真实缺陷及主分析／规则开发暴露，区分仅标题／文件语境相近与同机制；必要的提交说明和旧源码解封须登记为资格阅读。通过既定Claude Code＋AWS-Claude-Sonnet-5主分析路线审查提供者、公共消费者、同一状态及首次消费要求；一旦用于选例或修改规则，就不能再把该材料当未参与开发的盲测。资格阅读与冻结方法下的父版检测应分角色，后者不提供修复diff、旧标签或预期谓词。失败或不适用如实保存，不套self规则。

随后本轮资格阅读已执行，结果见[资格与条件覆盖复核](qualification_review.md)：两项预备项未进入正式对照，新增RISC-V项仅作能力维护辅助候选。两次Claude完整交付，第二次候选遗漏关键true分支等错误未自动采纳；严格独立正／正常仍0/0。下一操作以该报告及当前代办为准，回到N1受限自动提取，不继续为凑正例扩大该辅助案例运行。

N2后续接收审核后的契约、有限合法配置池和候选观测适配器，输出选择理由与待验证关系。其验收比较同预算朴素配对及最终状态观察，拒绝不可达路径、预标故障格和只加已知日志的“创新”主张。本轮未实现配置搜索、自动插桩或内核harness。R3继续暂缓。

重现命令（在内层项目目录，使用项目Python）：

```text
python -B -m unittest tests.test_contract_protocol -v
python -B experiments/case_taxonomy/contract_protocol_20261016/replay_known.py
```
