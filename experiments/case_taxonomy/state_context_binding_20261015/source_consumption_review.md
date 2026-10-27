# 源码消费位置与归档观测的独立复核

2026-10-15。独立助手只读核对上一阶段两份固定源码请求、配对最终正文的围栏诊断视图、消融正式proposal，以及既有s390/x86观察源码、补丁、有效配置和四份原始日志。仅新增本报告与consumption_evidence.json；没有外部调用、构建、内核启动、密钥读取或旧结果改写。

## 结论：可提出转接位置，不能回填为原位置已实测

两个模型原AST均已表达集合成员关系，原锚点保持不变：配对为contains(cpu_smt_mask(cpu), cpu)，消融为contains(smt_mask, cpu)；consumer均为sched_core_cpu_starting内的first_read。原5755行取得的是cpumask指针，不在这一行读取全部成员。观察lock_snapshot取自稍后的sched_core_lock内部，不能称为原5755行的直接观测。

在固定版本、实际提供者和同CPU作用域下，可以由研究侧／程序**另提出“候选执行点转接”**：保留原AST及原锚点，连接到原锁循环开始前的mask内容采样点。应另存目标函数、位置、来源、别名链和未决条件；这是研究侧定位工作，不是模型已经选对消费位置，也不是旧failed/unmapped变成正式通过。若声称原first_read时刻的值与稍后采样值相等，当前证据仍不足以无条件证明。

## 1. 公共消费者的实际顺序与必要条件

以下行号来自请求S_core/S_locks中未仪器化的固定父版88b604263f3d6eedae0b1c2c3bbd602d1e2e8775。

| 位置 | 具体行为 | 能支持和不能支持的推论 |
| --- | --- | --- |
| S_core 5753–5758 | 绑定参数cpu、局部smt_mask指针及当前cpu的rq；core_rq初始NULL。 | 可建立本函数的参数及局部别名，不表示mask内容已有正确成员。 |
| S_core 5760；S_locks 240–248 | 调用sched_core_lock；后者重新取同cpu的mask，保存本地中断状态，并遍历实际成员逐个锁对应rq。 | 内容消费发生于遍历，而非单纯取得指针。期望本CPU参与本组锁定时，目标位须属于该组；不能仅从“存在遍历”机械推出所有集合都必须含自己。 |
| S_core 5762–5766 | 检查当前rq初始自指；weight为1时直接解锁返回。 | weight==1不是非空断言，也不证明唯一成员是当前CPU。正常单成员情形还依赖集合身份及rq初始化。 |
| S_core 5769–5777 | 第一轮遍历跳过当前CPU，从其他成员中寻找core leader。 | “包含当前CPU才能由第一轮找到leader”是错误解释；self不是这一轮的leader。 |
| S_core 5779–5780 | 找不到leader时告警并退出。 | 空mask能够走到这一告警；正常多成员集合还须有满足条件的leader，self本身不是充分条件。 |
| S_core 5783–5789 | 第二轮为当前CPU安装core_rq，并核对组内成员一致性。 | 当前CPU不在集合时，其安装分支不执行；这与正确本CPU分组的语义相冲突。self必要性由组锁、初始化与安装语义联合支持，不能省略其适用条件。 |

归档观察源码中sched_init为各possible CPU初始化rq锁，并在CONFIG_SCHED_CORE下令rq->core=rq；这可补正常singleton与初始自指的源码依据，但不是上一轮模型已经给出的论证。原sched_core_cpu_starting的CONFIG_SCHED_CORE外壳以及!CORE空stub亦须保留。成员关系只是一个必要窄条件，不验证完整SMT成员、leader有效性、分组一致性或并发安全；其他合法必要条件不能因不同于contains而被排除。

## 2. 别名：静态同对象依据，不是地址实测

请求S_interface在CONFIG_SCHED_SMT且未由架构覆盖cpu_smt_mask时，返回topology_sibling_cpumask(cpu)。x86提供者为per_cpu(cpu_sibling_map, cpu)，s390提供者为cpu_topology[cpu].thread_mask。原core函数和sched_core_lock均以同一参数cpu调用getter，没有在所给局部路径中重新赋值smt_mask或写mask内容。

请求原文与既有目标预处理材料共同支持：在已固定架构/config及CPU1作用域中，两个局部指针指向同一提供对象。r4_note也从该CPU调用相同getter。**同对象不等于内容在整个区间不变。** 当前日志没有记录这些指针的地址，也没有监视所有CPU对mask的写入；不能从相同数值反推地址相同，亦不能从局部没有写语句推出全局不存在并发写入。扩展到其他版本或架构覆盖时须重新确认实际getter。

## 3. 观察lock_snapshot究竟覆盖什么

独立核对runtime/old_observer.patch及observer_sources/old/kernel/sched/core.c：观察代码先在sched_core_cpu_starting设置active，并记录core_enter；进入sched_core_lock后取得局部mask，采样mask/self/weight/rq_self/online及序号，随后才执行原local_irq_save与for_each_cpu锁循环。count在每次原锁调用完成后增加。快照在原sched_core_unlock之后输出，printed_after_unlock=1不是“解锁后重新读取mask”。

因此本样本可使用的是**锁前内容采样＋随后实际锁调用计数**。它不是循环各次读取的原子快照，不保证mask/self/weight这些分开的读取同时发生；更不证明从5755取得指针到解锁后的全部内容始终不变。关本地中断也不是跨CPU写入排除证明。

四份原始日志中CPU1/current1事件顺序为arch_before_notify→notify_enter→cpuhp_before→core_enter→lock_snapshot→core_exit→cpuhp_after→notify_exit→arch_after_notify，seq为1–9；实际共同调度阶段为90。相邻采样点到锁前采样的mask一致，锁计数与当次采样weight一致。旧s390为mask0/锁0，另外三格为mask2/锁1；四格当时online均0。它们是既有数据的直接摘录，**本报告未执行新模型AST，也未产生新的四格AST结果**。采样一致与计数吻合支持限定的单次启动观察，不排除未采到的瞬态变化或并发修改。

原始日志位置：旧s390的core_enter/lock_snapshot为85/149行；修复s390为85/87行；两版x86为108/109行。完整字段与config行号摘录见consumption_evidence.json。旧s390在online_ready后mask才变为2，最终状态不能代替首次消费观察。

## 4. 公共契约与架构履约见证要分开

| 核查项 | 当前依据及限度 |
| --- | --- |
| CORE/SMP/SMT生效 | 四份kernel.config及autoconf.h均实际启用SMP、SCHED_SMT、SCHED_CORE、64BIT，NR_CPUS=4；s390另启用SCHED_TOPOLOGY。CORE关闭时函数有空stub，不能把缺配置当正常。模型只列部分配置不是完整适用性认证。 |
| 共同消费者确实进入 | 既有CPUHP实际回调/目标对象和归档同CPU阶段90事件支持；单靠源码函数存在不够。 |
| x86准备 | 先加入cpu_sibling_setup_mask并构建self/兄弟关系，再notify；合法准备不依赖当前CPU已online。 |
| 旧s390准备 | notify先于online/update；cpu_thread_map又按online过滤。只把原update移前不改变过滤语义。 |
| 修复s390准备 | 先加入cpu_setup_mask并update，再notify，online随后发生。该修复源码只作研究侧解释，不是上一阶段受测模型输入。 |
| 实际范围 | 四次均普通双CPU初次启动；s390日志为SINGLE/facility0/mtid0。CONFIG_SCHED_SMT=y不表示实测了真实SMT硬件或多线程兄弟。HOTPLUG_CPU=y不表示实测了下线重入。 |

公共消费者材料可以支持一个局部必要关系，但要说“架构A满足、B暴露”，仍须补对应provider、有效配置、对象/阶段和传播路径。去架构组提出同一关系不使架构证据失去作用，也不能自动升级为跨架构违例。

## 5. 新版转接结果必须分别保存的内容

1. 模型原AST、原consumer/anchor/authority及正式协议状态；配对围栏诊断不是正式proposal。
2. 从同版输入扩展出的函数、参数、别名与条件编译依据，标明程序／研究侧来源，不回写成模型引用。
3. 拟转接目标为sched_core_lock内原循环前的内容采样，明确它与原指针取得点的区别。
4. 原始日志的CPU/阶段/样本字段、既有来源/配置绑定及采样限度。若要对原时刻作值等价结论，应额外证明区间稳定性；目前应保留不足。
5. 窄样本候选求值、必要性审查、架构履约与独立泛化分别报告；不得将contains作为唯一正确答案或用旧profile标签产生AST值。

当前可收束的是“原锚点保持，另提有条件的内容消费候选位置”；尚不能收束为无条件的原位置值映射或完整自动检测。全部仍是已读历史案例的开发与证据连接，没有未知样本泛化。

## 本地依据

- [上一阶段固定输入](../state_predicate_extract_20261015/requests/startup_target_pair.json)
- [配对纯围栏诊断正文](../state_predicate_extract_20261015/diagnostic/startup_target_pair.final_body.json)
- [消融正式proposal](../state_predicate_extract_20261015/proposals/startup_target_ablated.json)
- [旧观察补丁](../s390_arch_contract_20261013/runtime/old_observer.patch)
- [旧观察core源码](../s390_arch_contract_20261013/runtime/observer_sources/old/kernel/sched/core.c)
- [观察辅助头](../s390_arch_contract_20261013/runtime/observer_sources/old/include/linux/r4_observe.h)
- [既有运行与范围报告](../s390_arch_contract_20261013/runtime/README.md)
- [既有目标预处理材料](../s390_arch_contract_20261013/profiles/old_s390/preprocessed_facts.json)
