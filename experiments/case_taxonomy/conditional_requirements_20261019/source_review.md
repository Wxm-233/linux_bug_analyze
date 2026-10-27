# N2.14 公共条件与架构准备匹配的独立源码复核

2026-10-19。仅复用已保存完整定义、N2.13公共CFG和既有有限效果记录；没有编译、取新Git源、展开helper树、调用模型或读取新运行结果。本文件是独立助手的研究侧解释，不是人类专家金标准，也不把研究者登记的要求冒充程序自动学得。

## 先分材料层

- **当前非观测链**：N2.13 old_s390/old_x86 CFG及`consumer_preprocessing_20261016/old_{s390,x86}.json`中完整lock/getter。s390 `.config`为205e9f…、x86为881248…，与本轮CFG绑定；core.i分别7d7449…、23ea1f…。lock原定义`kernel/sched/core.c:240—248`，配置展开text局部L3取getter指针、L6关IRQ、L7—8按mask成员锁rq(t)。
- **s390提供者同配置链**：`provider_consumer_binding_20261017/{old,fixed}_s390.json`含mapper/updater/start完整定义、声明和ET_REL引用/定义。旧版88b604…，修复a05209…；修复资料是已有配置源码材料，不是本轮新CFG/运行，不能直接称固定版已通过新分析器。
- **x86来源与顺序**：`preparation_eligibility_20261016/source_material.json`的完整`smp_callin`原文（162—214）及其188—190行意图注释，支持该x86路径在通知前更新topology；192行map、208行notify。它不是配置展开或所有架构共同ABI。展开provider/getter/start/callin另在`aligned_contract_candidates_20261017/documents.json` D07/D08/D09/D12，但属于runtime派生配置a9264c…，不能替换本轮881248…非观测配置。

相同版本或profile名字不足以抹平这些分组。s390的符号定义、UND引用及重定位强于同形字段，但仍不是最终链接/运行地址证明。后文只给有依据的局部匹配和缺口，不跨组拼成自动整链。

## 最小公共要求

|候选|可支持的最小强度|适用性与不足|
|---|---|---|
|C1 目标锁覆盖|**若该mask锁循环承担保护本次目标rq内容访问的用途，且没有另一个已证保护方案**，则实际被锁集合应覆盖该合法目标。由lock只锁mask中的rq(t)，及starting锁后读目标rq->core、条件写目标关系推得；self∈mask只是这一用途下的必要候选|依据含研究者的锁保护用途解释；本函数单独不强制self。需绑定同目标/getter对象、实际遍历、正常锁效果及使用窗口稳定性；self不充分证明正确SMT组/初始化/并发|
|C2 搜索存在候选|非singleton且确实进入搜索、目标是继续关系更新而避开缺见证路线时，局部搜索需找到一个实际遍历的非target自指候选|N2.13 B9S9 true→B10S1→出口12支持选择与退出结构。不能把∃改为全组入口前已准备；真实rq合法、mask覆盖与builtin/WARN效果仍分开|
|C3 更新后检查|对实际到达第二循环的成员，在该成员可选target写入之后读取关系并作检查；若要求不触发关系诊断，应约束这个时点的关系|target-only store不重写其余成员。检查不是pre-state forall；跨asm继续、expect结果、完整遍历与稳定性不因正常CFG而证明|

`weight(mask)==1`会绕过搜索，因此若该分支已获证，**C2路线不适用**；这不等于C1得到满足或整个调用正常。单个其他CPU同样能走weight1短路，所以“非空/单成员/无诊断”均不能代替target覆盖。实际weight未知时是**不足**，不能记不适用。online/setup失败也不能拿来排除消费者scope：它们属于提供方履约资格，恰可能是失配来源。

## 准备匹配：来源、资格、期限分别保留

下表L均为已保存完整函数text的局部行，非JSON物理行。

|提供者|来源/目标与资格|顺序/期限|当前判断|
|---|---|---|---|
|old s390|mapper L6 clear、L7 !online拒绝、L9 set self；updater L6 possible循环、L7—8传同迭代目标thread_mask；getter返回cpu_topology[cpu].thread_mask|start L18 notify、L23 online、L24 update；若有效notify链在本次更新前读该目标mask，准备可能错过使用期限|**局部事实支持，有条件失配风险；实际履约不足**。不能由稍后set_online推得入口一定offline，不能排除此前准备/其他writer|
|fixed s390|mapper L7改查cpu_setup_mask；start L18设置该目标setup资格；updater/getter字段对应同上|start L18 setup→L19 update→L20 notify→L25 online|**资格/本地顺序有条件对齐，整体仍不足**。setup是允许准备，不是完成；还需实际possible覆盖、helper效果、同对象与首次使用绑定|
|old x86|runtime配置D07 L9先纳入sibling_setup；!has_mp分支L12写self，另一分支L20/L26—27按setup迭代、self或match_smt关系写sibling map；D09 getter返回目标per-CPU map|原文192 map早于208 notify且有本地注释意图；runtime D12 L31 map→L48 notify，D08 online在callin之后|**该路径源码意图与局部准备位置支持；当前非观测整链不足**。不同CPU表达式、实际迭代/写效应、其他成员语义及配置桥仍未自动闭合，不判x86整体正常|

旧/修复s390在研究者审核原语摘要和7项显式前提下，资格拒绝分支可条件解释为写空组；通过且非HW可条件解释为写出self。`preparation_effects_20261017/results.json`没有求实际guard，未证明前提；无前提均不足，HW路径仍为frontier。这可解释为何“仅提前update”仍可能被online资格挡住，或“仅换资格”仍可能缺首次使用前更新；不是本轮执行了不完整修复或证明真实mask值。

真正期限是公共内容消费点，不能把notify入口、getter取指针或函数返回当成唯一截止点。已有完整`notify_cpu_starting`只显示callback-range入口，`sched_cpu_starting:8836`显示调用core-starting；本轮不把缺失的有效注册/分派、实际目标/模式及整个链的可达性补成已证。C1应连接lock迭代中承担保护的实际使用，不能借前IRQ采样或旧运行打印反推精确遍历时值。

## 可保留的机制与下一步

可保留的架构机制是：公共用途可能在online之前要求目标信息可用；旧s390把生成资格系于较晚online阶段且本次更新在通知后，x86采用setup式来源并在通知前准备。差异沿架构getter进入同一公共锁/调度用途，不能简化为任意代码顺序错误。两边不必调用同名helper、使用相同原始mask字节，也不能因为一种架构是多数实现就把它当规范。

下一步只需把C1—C3的用途前提、对象、阶段、提供资格和缺口写成少量条件卡，由已有机器事实承担它真正证明的部分，人工接口依据单列。对每profile应输出“局部支持/条件风险＋整链不足”，而不是用online=false或缺证据直接给满足/不相关。若已有证据确证weight1或合法消费者路径未进入，才对相应子要求给不适用；不得提升为整体正常。非观测/运行及旧/修复来源继续分栏；本轮不新开CFG或模型支线。正式独立正/正常仍0/0。


## API用途摘要的有限补核

只读`api_contract_evidence.json`：旧/修复header同为23a26b…；weight534—541注释与短定义、for_each_cpu233—243注释与宏可以支持研究者审核的数量/遍历用途摘要；next209只有声明，不能作为完整实现证明。摘要前提须明确同一计数/遍历域：weight短定义使用nr_cpumask_bits，宏终止条件使用nr_cpu_ids，故需要mask在迭代逻辑域外无置位或另有计数域等价依据，以及mask和nr_cpu_ids在相关窗口稳定、合法目标/存储、正常调用和完整同一迭代域。不能仅凭摘要断定本次实际cardinality或迭代完成。

本轮C2仅限有同配置公共CFG的old_s390；fixed无本轮CFG，不借oldCFG给C2支持。fixed的C1可用自身完整lock/getter及显式锁用途前提，但依然不是无前提整体满足。本次Opus拒绝输出未用于正文或候选；要求/摘要均标助手研究侧审核来源，不计外部主模型自动生成或成功分析。首次独立next文档缺失失败保留，改以iterator API文档说明用途，不扩展helper链。
