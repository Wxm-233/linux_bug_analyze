# E/F原始交付与有限检查结果复核

复核范围：只读本轮父版材料包、原始prompt/final/receipt、冻结v2检查器及其已保存结果；未读child修复、`repair_evidence.json`或oracle，未修改任何方法、材料、回答，未重跑检查或模型。下文将实际返回原因与事后静态诊断分开。

## 实际结果是什么

两次交付receipt均为`complete_final_received`、exit 0、success、非error，实际及返回模型均为`AWS-Claude-Opus-5.5`，stop为`end_turn`、无refusal。两份回答均以唯一完整外层JSON fence解析。

| 单位 | E | F | 合计 |
|---|---:|---:|---:|
| 完整文件身份绑定source_bound | 7 | 7 | 14 |
| requirements/architecture_paths/recommended_checks候选 | 13 | 12 | 25 |
| 其中只完成引文绑定source_bound_candidate | 0 | 0 | 0 |
| local_checks | 6 | 6 | 12 |
| 其中verified_lexical_order / not_established | 0 / 0 | 0 / 0 | 0 / 0 |
| 其中insufficient | 6 | 6 | 12 |

14份文件身份绑定证明的是父版、路径、文本与采集材料对应。它不代表25项候选或12项局部关系被验证，也不代表14个问题。

局部项12次实际失败信息全部为`material_group_or_function_invalid`。这处检查位于函数定位、词法检查之前：模型将每项profile都写成了占位`CASE_parent`，而该文档的实际材料组是`E_parent`或`F_parent`。逐项函数名本身可在父版找到。因此本轮并未真正执行到这些局部项的定位器或锚点判断；不能将12个insufficient直接统计成12次定位器失败、模型语义错误或缺陷检出。

其余候选的实际失败信息为：12项architecture_paths全部`unknown_material_group`；6项requirements与7项recommended_checks全部`evidence_schema_mismatch`。前者原样复制了更长的占位`CASE_parent (material identity, not an architecture/configuration)`；后者使用了`{"document":"D01","lines":"a-b"}`，而冻结检查器只接受`document/start_line/end_line`三个键。先被profile拦下的architecture_paths、local_checks也使用相同的未支持引文格式。

## 模型与检查器的接口缺口

实际prompt只插入了`packet_schema.json`的`output`对象。该对象各处evidence仅为`[]`，顶层的`evidence`格式示例`{"document":"D01","start_line":1,"end_line":3}`没有进入prompt。profile示例也仍是未实例化占位，实际材料头才列出`E_parent/F_parent`。因此，本轮存在研究程序的schema交接缺口，模型同时未根据材料头替换占位。不能把全部格式不兼容归因于模型推理能力。

人工逐项读取原回答引文：E有43段、30个唯一跨度；F有42段、36个唯一跨度。共85段引文的文档ID及行号范围均落在各自提供的完整文件之内，但全部使用了未支持的`lines`键；E有8段、F有14段（合计22段）超过明确提示的24行上限。这22段属于回答未遵守已给出的长度要求，和schema缺失需分别记录。这里只核对其坐标存在，未由此认定引文支持候选语义。

下一轮如修正交接，应将精确引文对象和本任务实际材料组写进新协议及实例示例，并在调用前用合成输出核接口。不可修改本次原回答后覆盖成绩，也不可把格式映射后的追认当成本次冻结方法表现。

## 父版局部锚点的静态诊断（不是第二次运行结果）

人工对照12项的24个callee：各个标识符调用形态均位于模型指定的文件行号，所述词法前后在文本上也确实如此；未发现锚点行号或函数名捏造。但文本中存在调用不等于满足冻结检查器的支持范围。下表只阅读原函数和冻结实现推知潜在阻碍，未修正profile/evidence、未调用checker、未补支持。

| 项 | 父版坐标 | 静态诊断 |
|---|---|---|
| E-L1 | D05 `arch_cpu_finalize_init`；2314→2320 | 定义在2312行为`void __init ...`，return后的`__init`不属于旧定位器声明正则。两个锚点本身是独立语句。 |
| E-L2 | D01 `cpu_up`；1702→1707 | 定义可匹配，但完整函数1686/1688行含原始`#if/#endif`，旧词法器拒绝未处理指令；且第一项是if条件调用、第二项是赋值右侧调用，均超出独立调用语句支持。 |
| E-L3 | D01 `bringup_wait_for_ap_online`；760→774 | 第二项是`if (!cpu_smt_allowed(cpu))`条件调用，超出独立调用语句支持；它不是行号错误。 |
| E-L4 | D01 `bringup_nonboot_cpus`；1848→1852 | 定义1845行为`void __init ...`不匹配旧定位器；第一项还是if条件调用。 |
| E-L5 | D04 `ap_starting`；206→218 | `static void`定义和两个独立语句在已披露的语法范围内；未看到明显定位/锚点语法阻碍，但本轮未正式验证。 |
| E-L6 | D04 `start_secondary`；287→294 | 定义239行为`static void notrace ...`，return后的`notrace`不匹配旧定位器。 |
| F-L1 | D05 `secondary_start_kernel`；244→264 | 定义203行为`asmlinkage notrace void ...`，前置修饰符不属于旧定位器支持集合。 |
| F-L2 | D05 `smp_prepare_cpus`；730→733 | 定义723行为`void __init ...`不匹配旧定位器。 |
| F-L3 | D05 `__cpu_disable`；309→316 | 普通int定义、两个独立语句在已披露范围内；完整函数300—325行无内部预处理指令。未正式验证。 |
| F-L4 | D01 `init_cpu_capacity_callback`；417→418 | `static int`与函数名分为393/394两行；旧正则的空白允许换行，因此不能误记为定位器失败。两个调用是同一if块内独立语句；外围`#ifdef CONFIG_CPU_FREQ`不在函数切片内，但配置适用仍未知。未正式验证。 |
| F-L5 | D01 `topology_init_cpu_capacity_cppc`；379→380 | 普通void定义和两个独立语句在已披露范围内；外围`#ifdef CONFIG_ACPI_CPPC_LIB`不证明真实选择。未正式验证。 |
| F-L6 | D04 `sched_init_domains`；2608→2614 | 定义2599行为`int __init ...`不匹配旧定位器；第二项还是赋值右侧调用。 |

按最先可见的潜在语法阻碍分组：6项有定义修饰符不支持，1项完整函数有未处理指令，1项剩余调用嵌在if条件中，另外4项未看到明显的局部语法阻碍。前述分组不是checker补跑统计，更不是8项模型错误、4项检测成功。一些模型项确实违反prompt所要求的独立调用语句，另一些则是窄定位器无法处理正常内核声明。全部候选仍缺配置、控制流、实际对象与准备效果证明。

## 可得与不可得结论

本轮取得了两份完整的父版分析回答与14份材料身份绑定，但冻结端到端接口未产生任何正式引文绑定候选或局部词法关系。本轮主要暴露了schema实例化、引文协议和有限语法适配的断点；仅凭这些结果不能评价模型是否推导出了正确完整契约，也不能宣称自动检查已检出新问题、可泛化到新架构或已形成真实跨架构对照。

后续若研究语义质量，需将程序接口不足与模型候选内容分别评议，并继续保持父版推导、child盲判及配置/运行证据的独立性。局部调用顺序即便受支持，也不证明准备已完成或某架构已经满足公共消费者要求。

## 记录身份

| 文件 | SHA256 |
|---|---|
| candidate_checks_E.json | `8ab55ef9d608e600edb2ecb0058923f217bad3c4f4a72a9890b546a1cb33a042` |
| candidate_checks_F.json | `b595e1a74cec0161d4a75bd68e5426bff1239b47ba841b38921917a5de7a6924` |
| E原final.md | `1a689af97d1543e22447289262f6926c920045d3748f7344059a75a4953696b3` |
| F原final.md | `e54d92d51b6db2a09f587eafcb5de24fbbaffa01b34e913a7293a8bc25412005` |

prompt身份记录需区分磁盘字节和提交文本：Windows文件含CRLF，`read_text()`后的LF文本摘要才与packet_manifest和call_plan的prompt_sha256一致。E提交文本为`f6b0a866ab9c038bcf4ca059a455c29aa0d53369eebe31ce537795f0b13e3180`，F为`1b59f7eb9f9d1b3bcb7ccd39a739d18e1c792b12be22e00fa2229aead8af5bb4`；两份原磁盘文件摘要分别为`000fd7e4aea08e22f421783cb159f3f2367bb31f229c9afec6f92e6de6c7661d`和`c6392ab451e8247687624e6c784433465a0a9ba5f3bb46d00c51a3917094f5aa`。不能将文本摘要误称为原磁盘文件字节摘要。
