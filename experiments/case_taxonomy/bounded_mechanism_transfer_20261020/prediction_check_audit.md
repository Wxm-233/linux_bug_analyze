# N2.17 父版预测与程序核对的限域审计

2026-10-20。只读 G/H 的 documents、candidate_checks、原始 final/receipt/call_plan 和核对入口及其复用方法。未读 `repair_evidence.json`、独立 oracle 或修复正文；未修改方法、回答或已存结果，未重跑检查、调用模型或补源。本文件不裁定两项是否为实际缺陷、正常实现或独立同机制样本。

## 交付与统计单位

两次均由 Windows 原生 Claude Code 2.1.301／`AWS-Claude-Opus-5.5` 返回完整 final：型号一致、exit 0、success、end_turn、无 refusal。G 为唯一完整外层 JSON fence，H 为裸 JSON。完整交付和格式可解析不表示分析正确。

| 项目 | G | H |
|---|---:|---:|
| 父版原始文件／材料绑定 | 8／8 | 8／8 |
| 要求、架构路径、建议检查项 | 3＋5＋3＝11 | 3＋4＋3＝10 |
| 仅来源与引用绑定通过 | 10 | 7 |
| 候选项因引用跨度不足拒收 | 1 | 3 |
| 局部顺序项 | 6 | 4 |
| `verified_lexical_order` | 1 | 2 |
| 局部项 `insufficient` | 5 | 2 |

共16份文件、21个候选项、10个局部项，不是16或21个缺陷。三个词法通过也不是三个契约成立或三个检测成功。重新核对两包各文档文本 SHA 与文件身份字段一致，两个原始 final SHA 与保存结果一致；没有把材料组 `G_parent/H_parent` 当作实际架构／配置证明。

原答四个结构化组中的 evidence 共 G 61段（40个不同的 document/start/end）、H 47段（34个不同跨度）。按文档存在、整型行号、原文范围和每段≤24行检查，G有60段满足格式／范围、H有44段满足；这仍不证明引文支持文字结论。唯一跨度按每个包内计数，不跨包合并同名 D 编号。

## 拒收原因与局部支持边界

- G R2 的 D07:626–677 共52行。模型自己声明该段超限并建议拆分，但原回答没有实际拆分，因此整个 R2 候选绑定保留 `evidence_line_range_invalid`，未人工修复；其建议第二段650–677仍为28行，也不满足24行上限。
- H architecture_paths[0] 的 D05:845–870为26行，[1] 的 D05:669–701为33行；T2 的 D04:2155–2185为31行。三个候选项均因相同跨度门槛拒收，不代表对应语义已被反证。
- G L1/L2 的 `setup_arch`（D03:622）、L3 的 `of_fill_in_cpu_data`（D02:587）、L4 的 `start_early_boot`（D03:352）实际声明均为 `void __init ...`；冻结定位器只接受返回类型前的限定词，故返回“Expected one complete supported definition ... found 0”。L6 的 D07:203 为 `asmlinkage notrace void secondary_start_kernel`，也超出其声明支持范围。函数确实存在，不能把这五项记为模型虚构函数或已证顺序错误。
- H L2 的 D01:1353 同样是 `void __init smp_prepare_cpus_common`，属于定位器支持不足。L3已定位普通声明，但完整函数包含 D06:1715的 `#ifdef CONFIG_X86_32`，词法器拒绝未处理预处理指令；不能删分支或换配置后追记本轮成功。
- G L5只核实 `smp_callin` 内 `notify_cpu_starting`（D04:134）在 `local_irq_enable`（:141）之前。H L1只核实 `smp_store_cpu_info`（D01:188）在 `set_cpu_sibling_map`（:194）之前；L4只核实 `arch_update_cpu_topology`（D04:2348）在 `asym_cpu_capacity_scan`（:2349）之前。均为受支持独立调用形状的词法坐标比较，不证明真实分支、调用效果、对象相同或首次实际消费期限。

## G R1 的条件化还不能直接执行为违约判定

R1已经明确区分 SMP、sun4u／hypervisor，保留固件编号、`nr_cpu_ids`、枚举与公共启动顺序未知；把稀疏编号写成待验证假说而非已观测事件。这足以保留一项有源码线索的条件候选，尚不足以成为已证要求或可直接判违约的完整前提。

父版 D04:1219–1231显示，重写后的 possible 是 `[0,min(weight(Q_before),nr_cpu_ids))`；是否丢失 present 成员，取决于此前 present 集合 P 与 possible 集合 Q 的关系、完整写入者、调用时点和截断上限。不能把“编号稀疏”单独当作充分触发条件，也不能把“致密”单独当作满足证明。原答 architecture_paths 中“只有当OF集合为致密前缀才满足”的必要性措辞，比这些已知条件更强。

此外，“ARM64 的这一局部构造在遍历 possible 时置 present”不等于已核全部写入和共同启动路径；原答一面称其“合法对照”，一面 assessment 仍为 insufficient，应以后者为准，不能计正常样本。T1所提 `cpu_up` 错误消息也须绑定合法输入、同一对象和相关状态来源，单条拒绝消息不自动证明接口违约。尚需独立规范、合法配置及实际路径，不能由修复追认旧要求。

## H 没有提出 HYBRID 条件关系

原 final 未出现 `HYBRID`、混合核或异构核相关论述。父版包 D07:386确有 `X86_FEATURE_HYBRID_CPU` 定义，但模型主要提出 CLS⊆MC、掩码划分性质及 NUMA层表准备时机，并讨论 Intel／AMD／Hygon来源差别。提到厂商差异不等于提出混合核／核型条件怎样影响公共调度用途。

这只能记为本次父版预测的关注范围，没有借修复真值判漏检或成功。R1/R2的父子包含与同层划分还对应包内已有公共检查，引用绑定不证明本项目新提取了有效检测规则。H自己保留实际硬件、配置、调用链未知；其“WARN足以证实违约”的文字也不能替代具体配置、对象、用途和因果裁定。

## 程序实际核对的内容

`check_parent_predictions.py`核登记的文档包、输入 artifact、方法版本与发送文本摘要，检查交付门槛后原样解析回答；复用的 binder核文件文本、parent/material-group声明与来源指针的一致性。候选项通过只表示引用可绑定；没有机器证明 statement、basis、applicability、eligibility、deadline、predicate 等语义内容。历史 parent 真实性仍依赖上游采集与登记，不是本核对器从 Git 独立重建。

本轮没有把原始 C 转成实际配置下的翻译单元，没有证明宏的最终有效定义、控制流、准备效果、相同对象或跨架构传播，也没有更新正式 features。输出已经明确 `semantic_or_effect_proof=false`、`formal_features_updated=false`。因此可以报告“原始回答可交付、部分引文受程序约束、普通声明／预处理支持受限”，不能据此报告自动要求推导成功率、实际违约、跨架构正常对照或 N2选择增益。

## 用量与身份

| 调用 | 可见客户端报告token | 保守记账token | 原预占 | 耗时 |
|---|---:|---:|---:|---:|
| G | 318356 | 318356 | 200000 | 272.750秒 |
| H | 353078 | 353078 | 200000 | 177.843秒 |

可见与保守是同次任务的两种记录口径，不能相加；原预占也不能再加到本次保守值。按同一口径汇总两任务为671434 token，两份收据的 `usage_known=false`；CLI内部恢复和最终计费未独立测得，不能将可见计数当作完整平台账单。

- 原始 final SHA256：G `53e040ec6033c2749c134fb9f0dd132d1e4983de3ff234b72062894b497c7de7`；H `f6ddea65fae04cab22d44c7581bfbcc99975b3c4dd5d1fa70f2b29b9c6855560`。
- 已存程序结果 SHA256：G `a8943914aa1b1429c1d1947384684bd3b2d0804ce9642dae3f2688f577bdeed6`；H `fe0e74b569467b81bef15db2856b912bc8d1fea94f63041f132763d1963eb884`。
- 本次所审入口 SHA256：`a87d9ae9903cb3204105192ef9664aedd17b7617a83b80d158dbfd9943833b63`。
