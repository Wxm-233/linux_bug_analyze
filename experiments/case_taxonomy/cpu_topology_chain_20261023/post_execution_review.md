# N2.23 执行后独立有限复核

2026-10-23。助手研究侧只读审核，已接触本案例及本轮人工契约，不是独立留出或人类专家金标准。核对归档原文、SHA、结果与既有测试收据；未复跑旧helper、候选、测试、模型、编译或内核。

## 结论及层次

**无实质阻断。** v2四格原样本与16条方法控制已保存，关系结果与原日志一致；未将采样抬为精确消费或完整链。完成的是已读案例的归档/条件核心接线和证据缺失控制，不是自动推导契约、新缺陷检出或独立泛化。

## 身份、版本及首次失败

- 新清单十一项SHA全部匹配；原38项归档输入及本轮35项去重artifact也全部匹配。清单/结果正确绑定`trial_inputs.json`，原人工来源审查未改。38和35为重叠的材料集合，不能相加算新证据或案例。
- `contract_protocol.py`、adapter、输入及14项方法测试文件摘要保持冻结值。十四测试PASS收据仍为原记录，本复核未重跑；它们不计独立Linux问题/正常例。
- 原driver与原manifest保留，原`results.json`不存在。`execution_initial_failure.json`摘要仍为`5094394a60ef78bad2ba6c6e5b80e1aef4a7b0cb859db31a782dfb4cd87af87d`，记录首次在CRLF最终成员诊断处断言，首baseline曾返回但未保存其值。不能补造首轮评分或称首轮完成。
- v2只修诊断行尾CRLF及独立输出/清单/门控名称，以新入口重放。v2清单摘要`6d123a5b27a4dd7997afbc17d96d823f5e0bce240f9026007d6ac44267cf9275`，结果与之吻合。这是失败后的已读开发重放，不是冻结未知输入首次成功；没有新增编译、内核启动或项目模型。

## 原始采样与未改核心求值

各raw路径为`../s390_arch_contract_20261013/runtime/profiles/<profile>/qemu_boot.stdout.log`。四格选中的CPU/current均1、seq均5，均为IRQ关闭前取得、unlock后打印的lock_snapshot。

| profile / raw行 | mask / self / weight / locks / online | 归档绑定 | 人工用途前提下的采样成员关系 |
| --- | --- | --- | --- |
| old_s390 /149 | 0 /0 /0 /0 /0 | bound | violated |
| fixed_s390 /87 | 2 /1 /1 /1 /0 | bound | satisfied |
| old_x86 /109 | 2 /1 /1 /1 /0 | bound | satisfied |
| fixed_x86 /109 | 2 /1 /1 /1 /0 | bound | satisfied |

这些成员与CPU值来自raw核对，不是从旧status/predicates或版本标签取答案。它们只说明给定研究者用途、对象角色和样本定义后，所审**采样关系**是否成立。四格`relation_at_deadline`及`whole_path`全为insufficient；`provider_preparation_effect_proved`、`physical_lock_object_proved`、`exact_consumption_value_proved`及`continuous_stability_proved`均保持false。

最后一次sysfs `cpu1_threads`读数均为逻辑成员[1]，所以final_state_only诊断四true；采样online四false。前者不能区分旧s390早期空集合，后者不能作为准备完成的通用要求。它们只是本既有案例中两个简化观察的局限，不是一般准确率或已经证明的替代检测算法。

## 十六条控制的拒判来源

四类控制各覆盖四profile，均返回status不足，没有制造新kernel样本：

| 控制 | 处理层及原理由 | 应如何解释 |
| --- | --- | --- |
| missing_effect_value | adapter：`sample_fact_set_missing_or_unsupported` | 缺成员值不能评价，不得用版本/末端值补齐 |
| missing_object_review | binding仍bound；core：`missing/wrong evidence role: review.object_binding` | 字节和事件可绑定，但人工对象审核缺失，语义求值不足。wrapper reasons为空不是漏检，应读取core reasons |
| wrong_profile | adapter：`profile_revision_or_arch_mismatch` | 错身份不混入另一格 |
| sample_promoted_to_consumption | adapter：`sample_promoted_or_relabelled` | 不能改名借采样制造消费期限证据 |

这些结果核验受限接线的门槛，不说明十六个真实错误已检出，也不能据“全部拒收”推独立误报率/召回率。

## 保留的人工依赖与不足

supported的provider只指本地probe/getter，object只指逻辑样本角色；完整原生准备、物理锁目标别名没有被自动认证。deadline的supported仅为源码中另一个内容遍历位置的身份，样本与其不同，真实期限取值持续不足。旧foundation名称保留为归档背景，不进入新核心充作连续稳定或提供者因果证明；旧s390的prepared=-1也没有被解释为false。

因此，本轮能支持“带人工用途前提的样本关系被程序求值，身份/证据缺失时拒判”的结论；不能称准备资格→全部实际效果→同一物理对象→精确首次公共消费已由机器完整接通。后续应据这个明确边界收束CPU-B的有限小闭环，而不是为清空unknown继续扩helper或运行网格。

新增案例、正式独立正/正常、模型、编译、内核启动均0；历史四格启动仍是一项既有案例。N1/N2完整能力未完成，R3继续暂缓。
