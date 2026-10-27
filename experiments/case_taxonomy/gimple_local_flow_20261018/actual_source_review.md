# N2.12 真实GIMPLE局部事实及原始比较复核

方法与scorer冻结后才解封reference。本复核读取原分析输出、原比较结果及已冻结源码参照，没有改写它们、修改分析器或重跑source。本人是reference编写助手，参照是助手手工解释的已读源码开发核对，不是人类专家金标准或新Linux留出。

## 身份和原始结果

method登记文件和reference登记文件SHA均一致；两个输入与binding的SHA逐项吻合。逐事件核对`raw == input[start_offset:end_offset]`均成立，说明本次事件留存了精确原文区间。source locus与section局部行号仍应分开；原C列/运行对象身份不因这项核对而证明。

原始`source_check_results.json`保持**20项中2 match、2 mismatch、16 insufficient**，不回改。reference使用`field_load/field_store/condition/assignment`，分析器公开输出为`load/store/branch/scalar_assign`，scorer逐字比较kind未做交接映射。我提交的reference与执行器未统一这些名称，是reference—adapter接口缺口；不能把空锚点都解释成分析器未提取。

尤其F02两项在局部指定范围内没有opaque，所以接口空选集被原scorer记为mismatch；实际对应store已经存在。这两项不能当成“分析器漏了真实字段写入”。但它们的原状态必须保留，不以人工核对偷偷追认本轮通过。

## 原输出已经具备的局部事实

两份均为`partial_local_facts`，s390 179事件、x86 182事件，各37条局部依赖。这些是机器事实节点/边数量，不是案例或契约数。两者都输出3个显式`rq->core`读、1个写，以及3个per-CPU indexed load；不能把6个load全说成字段读。现有field属性只有core，未从路径`.cache/core.c`、asm指令或D.xxx/cpu.xxx生成假field。12个call与6/9个asm分列；本次不把asm算return。

|核对关系|s390机器输出|x86机器输出|结论边界|
|---|---|---|---|
|候选字段读→比较|E88→E89，变量_16，region77|E89→E90，变量_16，region79|局部字段读取值与紧随比较已连接，不证明rq指向哪一CPU或整个搜索契约|
|后续字段读→关系比较|E149→E150，变量_29，region141|E151→E152，变量_29，region145|后续显式读的临时值已进入比较；不是先前store到该读的memory alias/效果证明|
|见证赋值后的goto|E92→实际label E100，D.80224|E93→实际label E101，D.81134|原比较已确认此两项。它是显示目标，不证明首命中执行、支配或全函数CFG|
|skip-target if两分支|E67的true/false标签均实际存在|E68的true/false标签均实际存在|原F07因condition/branch名称空锚点不足，不能当机器没有分支事实；路径可达性仍未证明|
|初始warning flag跨效果读取|E44的定义不连接到E54；后者明确live_in_or_barrier_cleared|E44不连接到E55；后者同样明确unresolved|不是找不到锚点当成功：两端存在，间有scope、label/call/asm屏障，保守未知被保留|

初始字段读还分别输出E42→E43的_5关系。目标条件store分别为E145/E147；store使用的rq、core_rq仍有明确live-in/屏障未知。后续比较中的core_rq也保持未解析，程序没有把文本上最近一次见证赋值跨goto/label/asm强行接过来。这种保守限制符合预登记局部区域范围；37条边不是全局reaching-def或运行值关系。

## 仍不足的部分

两份都有E16：`void unlock = <<< error >>>;`，保持opaque。它是GCC转储的标签伪声明，不是编译失败；但冻结scorer没有证明该未知区段与全局计数无关，故全函数数量/零事件认证继续不足。返回事件为空、field仅core等可以作为对当前已提取事实的只读核对，不能越过该机器coverage限制追认全函数完备性。

诊断asm和scope/try/finally/label均保持屏障，call result也标未知。原程序尚不证明跨屏障值保持、store/load对象同一、准备效果、架构provider资格、完整通知外链、稳定性或首次实际消费；更不从语句图直接推出规范义务。所核的局部事实未见错误连接，不等于已完成所有事件的语义正确性证明。

## 仅kind适配后继的边界

另登记一个**工程适配回放**可以接受：冻结完整通用kind对应表并说明这是表示层翻译；只读取同一已冻结`program_results.json`，不重跑分析器、不改源码/expected、不根据具体答案增加源行或变量特判。field_load映射仍必须要求field属性，不能误把indexed load也算字段；assignment映射只是标量事件名，不改变值等价或依赖含义。多kind集合、field_not_in和真正缺失锚点均须保留原约束。

原始2/2/16结果必须与新适配回放并列。适配后查到已存在事件，不能记为新分析算法或本轮独立成绩；20项均已读，只能是开发回放。全局opaque引起的不足不应为追20/20而事后缩窄认证范围；若要调整coverage协议，须另作有依据的新版本评价。未来仍应围绕真实GIMPLE的局部值源与控制证据推进，不把接口修复当作跨架构契约已闭合。正式Linux独立正/正常维持0/0。


## 已执行的词汇适配回放补充

后继`schema_bridge/protocol_pre.json`已另行登记，`replay.py`只深拷贝原事实并映射kind，保存original_kind；逐事件还原比较、dependency/control edge不变断言均在脚本中。现存保护文件SHA核对一致，未执行新source分析，也未改变原始2 match / 2 mismatch / 16 insufficient。

`developer_replay_results.json`为**12 match、8 insufficient**：各profile的局部store、候选读到比较、显示goto、if双目标、跨效果unresolved及后续读到比较可由名称映射后的既有事实定位；其余各4项全局计数仍因E16 opaque不足。12不是检测率、新算法增益或独立成绩；它只说明统一接口后能对照早已存在的开发事实。不能为追20/20而删除opaque或缩小原认证范围。

另核对asm上下文：真实s390有6个asm事件（3次per-CPU空asm及3次WARN诊断）；x86有9个（同样3次per-CPU空asm，每次WARN另有主诊断和discard.reachable独立asm，共6次）。冻结reference的F03 manual_context_only实际分别登记6和9，与原文一致；这部分不是评分项，不应误报为分析器漏提或参照双边均填6。call计数12与这些asm事件分开，不能相加后称函数调用数。
