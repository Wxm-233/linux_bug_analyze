# N2.23 执行前：契约与证据台账审查

2026-10-23。独立助手研究侧复核，不是人类专家标注；已读开发材料。已只读核`prepare_trial.py`、所生成`trial_inputs.json`、原归档加载入口及未改契约核心的有关判定范围，未运行候选、测试、编译或模型。`reviewed_chain.md`已纳入输入SHA，本次没有修改它。

## 构造与来源核对

四格各用自己的revision/config/log构造context，采样固定为CPU1的`lock_snapshot`，sample_id与后续`mask_content_iteration`名称不同。台账列出artifact_key、实际SHA和完整文件行界；只读核对35项去重artifact摘要、各document声明行界及所有引用范围均匹配，旧输入清单计38项。这些数是材料数，不是案例或运行数。

新contract/record没有导入旧status/predicates。仍保留的`foundation`是旧归档验收背景，其中`same_mask_until_first_consumer`只能理解为若干观察位置取值相同，不能解释为连续稳定；`source_single_mode_self_rule`、`source_provider_gate_and_preparation_order`等旧旗标也不自动给出本轮必要性、完整准备效果或物理绑定。正式核心不得借这些名字补语义。

`members`按已固定NR_CPUS=4的有限观察域从原mask取位，target由所选原事件CPU得到；本构造不支持任意CPU数、任意日志或复杂映射。selected_path还依赖该次路径/事件存在的归档核对，不应将配置打开本身等同路径实际执行。原日志选择、用途、作用范围和候选表达式均是研究者指定。

## supported的允许含义

当前claims表述足够窄，无需为求通过制造更强真值，也不应因同为supported就统称完整链已证：

- authority/consumer_requirement：在目标锁保护且无其他已证明替代保护的**人工条件性用途前提**下，成员覆盖是一项必要关系；不是从程序自动得到的通用规范。
- provider_binding：只绑定产生本条日志的本地probe/getter，不认证全部原生准备、mapper作用或所有写者。
- object_binding：只审核所选事件CPU与probe参数的逻辑样本角色，不认证物理锁地址/别名、跨架构相同物理对象。
- deadline_binding：只识别源码中之后应审的原内容遍历位置，不是已测到一个精确运行事件或其值。故`relation_at_deadline`和完整契约仍必须不足。
- observation_binding/facts：仅为IRQ关闭前的mask采样及其事件身份；打印在unlock后，打印位置不等于采样位置。字段关系不自动移到真实消费点。

契约声明`sufficient_for_correctness=false`、研究者field_origins，记录固定`sample_kind=sample`且观察与deadline分开，与上述边界一致。虽然核心接受这些外部审核输入后可以判采样关系，它仍不能替外部审核证明前提。不能据四格预期答案反向改claim。

## 候选运行前剩余门槛

当前只完成构造/语义范围审查，尚未审最终`sample_adapter`及运行driver，**不是最终执行放行**。后续需核它们只验SHA/profile/event/facts，不自动添加语义claim或把旧判断作为事实；错配置、缺效果、缺对象审核及假消费控制应保留不足。20条记录只是4个既有样本及4类×4方法控制，不是20个新案例或启动。

本轮报告须分采样命题、实际deadline、完整准备/绑定链三个层次。实际效果未闭合、物理别名、精确遍历值、稳定窗口继续不足；不扩helper、平台或运行矩阵，R3继续暂缓。

## 最终adapter/driver及执行门控

已只读核`sample_adapter.py`、14项合成开发测试与`run_chain_trial.py`，十项`method_manifest.json`摘要均与现文件一致，主`results.json`尚不存在。adapter摘要为`2d38604999a76e4e5892e72187f9f6ac0c791cd98b8c39fdfe5229d9c6cb03d6`，driver摘要为`acfb8b47512bc84e406d8fe08c4f2fa379e4d233012a75a21c7c6f7c711968c1`。14测试PASS只引用已存收据，本复核未重跑；它们是适配器开发验收，不是独立Linux案例。

adapter核所供bytes/SHA、四profile的revision/arch/config/autoconf、观察源码manifest、镜像与命令的归档链接、实际PID1身份、唯一CPU1原日志行/序号及原mask成员。它不新认证ELF、不新增语义claim，外部准备效果/物理锁对象/精确消费值/连续稳定标志均保持false。record成员与target须与raw一致；旧status/predicates、原警告和最终成员不作为关系答案。缺审核或证据仍由未改core返回不足，sample重命名为消费在适配器处拒收。

driver仅运行四个原样本及四类×四证据移除/变更控制。最终成员和online只作旁列简化诊断，不进入core事实；prepared=-1也没有被转成布尔false。所有输入及核心摘要核对先于候选求值，不覆盖已存在结果。假消费控制、错profile、缺members和缺object审核应分别保留不足，不能将“拒收控制”记为真实缺陷检出。

**启动入口限定：**冻结driver只加入了其自身目录，未显式加入项目ROOT；应从内层项目根用模块入口`python -B -X utf8 -m experiments.case_taxonomy.cpu_topology_chain_20261023.run_chain_trial`，或显式提供等效项目PYTHONPATH。不得依赖绝对脚本启动时包恰好已安装。该入口限制不更改冻结方法或数据；门控不授权额外试跑以排查导入。

在上述入口和既定sample语义范围内无实质阻断，允许一次20条记录的开发求值；无新内核运行、编译或项目模型。门控不预判结果，也不授权将supported样本角色改称完整提供者因果链已证明。

EXECUTION_GATE: PASS

## 首次driver停止与v2有界修正

首次正式模块调用在原driver:48的最终成员诊断正则断言处停止，未保存`results.json`。原日志CRLF没有被原`([^\r\n]*)$`末尾消费；`execution_initial_failure.json`记录首baseline evaluator曾返回、结果未保存以及零新编译/启动/模型。不能将这次停止改写为首轮20条完成，也不根据未保存返回值补造首轮评分。

v2复制为`run_chain_trial_v2.py`，只把最终状态诊断的行尾改为`\r?$`，并改独立输出、清单及v2门控名称；核心、adapter、contract、record及事前关系不变。原driver/manifest/inputs保持。已核新清单十一文件均与当前SHA一致，previous绑定原清单，原adapter及14测试文件摘要未变；清单中四份raw的单个final诊断定位只作已读开发定位记录，不是新增案例或独立测试。

v2 driver SHA256为`7a2e52e580c31c74e54ae5650542d4868173fc7cd5ff669f548f61dcc7207ece`。允许以同一内层项目模块入口运行v2一次，保留结果与首次失败并列，不覆盖原件、不重新编译/启动。核对时原/v2结果均尚不存在。本复核没有执行候选、测试或正则重跑；v2不改变sample/真实deadline及完整链不足的边界。

V2_EXECUTION_GATE: PASS
