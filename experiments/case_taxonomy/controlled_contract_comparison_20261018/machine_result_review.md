# X原回答的程序结果限域复核

只读X原final、原14份文档、冻结检查器及已保存`paired_checks_X.json`；未读独立语义评分或raw_semantic_review，未读Y任何partial/assistant/final，也未改代码、原回答或重跑。

X原final摘要为`7c333a906f178fa01d0807d3ee33265b6098a2dc07730791ca6b44d06db9b25e`，与程序记录一致。14份文档均为`source_bound`。原回答有3项要求、6项架构路径、3项建议检查、6项局部词法关系；12项非局部候选中11项仅完成引文身份绑定，1项不足。6项局部结果为4项`verified_lexical_order`、2项`insufficient`，没有`not_established`。

## 四项通过实际核对了什么

| 项 | 文档与函数 | 程序核对的词法顺序 |
|---|---|---|
| L1 | D01 / old_s390 / smp_start_secondary | 第19行notify_cpu_starting在第26行update_cpu_masks之前 |
| L2 | D01 / old_s390 / smp_start_secondary | 第19行notify_cpu_starting在第25行set_cpu_online之前 |
| L3 | D12 / old_x86 / smp_callin | 第31行set_cpu_sibling_map在第48行notify_cpu_starting之前 |
| L4 | D08 / old_x86 / start_secondary | 第18行smp_callin在第38行set_cpu_online之前 |

人工只核对了上述源位置与报告对应，未据此评分模型契约。四项通过只表示原文的有限调用形态、锚点和先后与模型给定的`expected`一致。L1的“通知在更新之前”通过，尤其不能解释为程序认为该准备顺序正确。程序没有判断契约应当要求哪种顺序，也没有证明实际执行、跨函数调用链、对应对象、全路径时点或准备效果。

## 两项不足是标签语法边界

L5（D05 / old_s390）和L6（D10 / old_x86）都提出sched_core_lock第10行在sched_core_unlock第43行之前。两个callee和行号确实存在；第42行是`unlock:`，第43行紧接解锁调用。冻结`_anchor`只接受前一个词法token为`;`、`{`或`}`的独立调用形态，此处前一个token为标签冒号`:`，所以解锁锚点不在支持上下文中。

两项实际返回原因均为`call_anchor_not_in_supported_expression_context`，同时保留“Missing or unsupported lexical anchor; not a semantic error verdict”。这两项不是模型捏造callee、行号错误或被证明的逆序；它们说明当前窄语法支持不足。没有为追分增加标签支持或重新核对。

## R1为何未完成引文绑定

R1实际原因是`evidence_line_range_invalid`。六段引文中，D05第19—43行跨度为25行，超过登记的单段24行上限；D05实际有51行，所以这不是引用了不存在的行。其余五段坐标与长度合法。程序按整项引文条件拒绝R1，不能把这个格式约束结果解释为R1语义错误，也不能手工拆分这段后追认通过。

按原回答逐段统计：requirements 16段、architecture_paths 26段、local_checks 8段、recommended_checks 8段，共58段、34个唯一跨度。58段均使用正确的document/start_line/end_line键，文档ID和坐标落在材料内；其中57段满足整型、文档范围及≤24行限制，仅上述1段超长。这里的合法仅指引用格式与坐标，不表示原文支持断言。11项`source_bound_candidate`也只认证来源和跨度，不自动认证候选要求、必要/充分性或架构因果解释。

本轮程序对同一原回答增加的是可追溯引用、有限词法关系与明确的拒判边界；没有把任何语义评分提高，也没有新增契约/效果证明。已知开发材料上的4项词法通过不能当作4个新案例、4个新缺陷或自动检测泛化成绩。Y不在本次内容复核范围内，不读取或恢复其拒绝内容。
