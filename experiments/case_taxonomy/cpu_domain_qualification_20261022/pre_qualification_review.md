# N2.20：父版材料与方法的资格前有限复核

2026-10-22，arch_check_review。本人已参与前期案例/方法开发及N2.19审阅，不能称全历史盲；**本轮未读新child正文、diff、资格oracle或任何模型回答**。仅核selection/protocol/material plans、方法版本、两父版包、manifest、包生成规则及实际prompt；源码阅读只用于定位共同用途边界。不增加材料或修改输入，没有CLI/WSL/API、编译和运行。

结论：**父版材料身份、通用提示及方法一致性通过；可以据此冻结后交隔离资格角色。** 这不是P01阳性资格或P02正常资格通过，更不授权立即付费分析。任一资格门槛不足仍应零调用收束，不补选、不补源。

## 1. 选择与固定范围

selection为既有500池中目的性元数据定位：P01一个候选、P02同父版LoongArch参考，无新正文后替换。未选metadata条目不是失败后的备用。P01标题涉及Xen/ACPI平台模式，协议已要求将平台模式与CPU ISA分开，不能因另取LoongArch材料便视为已证跨ISA问题。

两组各8份完整父版原文件，均为`0af2f6be1b4281385b618cb86ad946eded089ac8`，路径与initial_material_plan逐项、顺序一致。共16个材料条目、13个不同路径，3份公共文件在两组复用；不是16案例。supplement_sources为空，符合adaptive_parent_supplements=0；本次不提出额外补源方案。

## 2. 字节、行号和中性提示

对16份文档分别重算text SHA及Git blob，均与原来源行一致；source_binding所指artifact摘要、JSON索引原text、父版标识均匹配。文档包摘要、protocol/method摘要和prompt摘要均与manifest一致。两prompt末尾恰为各自8份全文的SOURCE元数据加逐行1起始行号，不额外插入源后评语或删改正文。

P01/P02及D01–D08为中性身份，实际prompt去掉材料组名差别后，指令/格式头相同。两prompt字节为272044、194587，均小于生成器600000限制。prompt未包含选定child hash、提交标题、缺陷/正常角色标签、资格结果或预期谓词；selection研究侧的reference身份没有传给模型。

通用focus沿用N2.19：命名空间、映射、选择数量域与准备/实际使用阶段。它是既有研究先验，不是本例的目标真值；不得因模型复述这些维度就记自动从零提取。要求允许空列表/insufficient，格式合成文档不在实际允许ID内。不能把原始ID一致、集合计数相同、所有possible已有现实物理映射或调用过准备函数当统一规范。

所有材料configuration/image/preprocessed摘要为null，kind为raw_source_file，提示明确未预处理分支及组名不证明配置。归档全文绑定不升级成有效TU、实际配置或运行证明。

## 3. 材料可见用途与不足边界

P01可见x86 ACPI入口、topology限额/possible准备、setup_arch的调用位置及Xen PV的CPU来源/准备入口。例如D03:1199–1211连接平台解析与topology初始化，D02:427–440是限额处理，D04有Xen的vCPU来源与smp_ops。它足以让资格角色研究“平台提供CPU容量，经逻辑域交给公共SMP”的源级候选，但本身不证明Xen ops确被选择、ACPI/配置实际状态、合法多CPU场景或具体公共错误。

P02可见LoongArch固件CPU编号到逻辑映射、present/possible设置，setup_arch中平台setup及prefill，后续prepare。D04:78–95区分enabled/disabled登记，D03:611–614给出setup调用位置，D01:568–579给出准备入口。共同D05/D06/D07提供cpumask语义、公共nr_cpu_ids重定界和SMP入口阶段。因此它有同用途定位依据，但实际固件/配置、回调选择及消费所需保证未由身份绑定确立，不能先认定正常。

本包可见公共setup_nr_cpu_ids/smp_init等入口，不等于完整公共CPU生命周期消费者与全部间接调用体已经闭合。资格审查应只对8文件所能支持的有限命题给出条件保证；不能把包外逻辑、缺定义或未有效分支填成正常/违约。缺材料时按既定停止条件记录，不扩树，也不要求所有实现同一种映射或准备方式。

## 4. 方法版本和预算澄清

原schema、raw adapter及六项登记组件、通用runner的当前SHA均与method_versions一致。包生成只绑定原文并复用同一schema，没有新目标解析/效果支持或人工预计算真值。case-specific旧参考记录不能冒充本轮已运行的完整pipeline；来源/引文、局部词法、语义、实际配置应分别报告。

新增`budget_interpretation_pre.json`在冻结/资格修复阅读前澄清：协议每任务400000是**外层预算预留和记账下界**；原runner默认200000保持不变，其call_plan不能误称400000。未来若双gate达标，每个已发任务按`max(400000, receipt保守计数, 已知可见计数)`记账，先终态再判断累计加下一项400000是否不超过1M；失败/不完整任务不按零计算。该澄清不改方法、prompt或runner，也不是实际账单硬上限。当前新模型调用为0；达双gate后才另登记调用。

## 5. 冻结及隔离条件

建议现在固定本轮材料、通用prompt、方法及本复核身份；之后资格角色才能读唯一选定修复，且不能据答案调整父版包。资格角色先只回eligible/insufficient，完整义务、正常保证和修复裁定不进入预测；主任务若提前读完整oracle，也不得据此改输入。若两门槛均通过，再按固定输入调用并保存预测后解封比较。

资格本身是研究侧人工/助手工作，不计自动N1成功；P01旧路径接触、P02未知接触和家族关系尚须单列，未命中历史检索不等于独立。没有新确认缺陷、正式独立正/正常、方法测试或运行被本次材料复核增加。
