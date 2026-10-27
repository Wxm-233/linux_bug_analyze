# N2.6 两项父版资格的独立复核

仅根据 `initial_sources.json`、已登记唯一补源计划及 `supplement_sources.json` 的原始父版源码判断。每项初始3份、补充4份，共7份完整文件；一次直接符号定位后不再补源。未读子提交说明/补丁或本轮模型回答。此文是研究侧资格记录，不作为主模型输入，不预设缺陷或正常。

## E：eligible，限条件接口问题

父版 `6eaae198076080886b9e7d57f4ae06fa782f90ef`。**足以开展一次并行能力门控、公共分阶段启动及数量域的条件候选分析；不足以检验完整primary集合准备履约或首次使用违约。**

- **架构提供与条件**：x86 `smpboot.c:1277–1289` 的 `arch_cpuhp_init_parallel_bringup` 在X86_64下检查平台许可，拒绝则返回false，接受则写 `smpboot_control=STARTUP_READ_APICID` 并返回true。`arch/x86/Kconfig:279–281` 给出SMP＋X86_64选择并行、SMP选择SMT热插拔、SMP＋X86_32选择split startup的条件。是源码条件，非实际构建配置或硬件有效性证明。
- **公共实际用途**：`kernel/cpu.c:1806–1838` 先消费架构许可返回值，拒绝则回到串行路径；接受且SMT-aware时取primary mask，对present集合求交，先进行primary的KICK_AP/ONLINE两阶段，再按在线数量调整预算并处理secondary集合。`bringup_nonboot_cpus:1845–1852` 是公共入口；`cpuhp_bringup_mask:1765–1785` 用mask、ncpus和目标阶段调用cpu_up并处理回滚。该调用体使“能力声明/输入集合与公共分阶段算法是否一致”成为实质接口问题，而不只是名称相似。
- **对象与阶段要求的依据**：`asm/topology.h:144–153` 将primary getter/测试绑定到 `__cpu_primary_thread_mask`；公共cpu.c:658–667区分SMT配置下的primary mask和非SMT的present mask。1819–1823注释明确给出x86微码更新时primary先启动的用途，cpuhotplug.h:25–41说明公共状态分段。可问这些条件下集合、数量和阶段应满足什么，不预先给模型规定正确答案。
- **关键缺口**：7份文件中可见primary对象定义（smpboot.c:107–108）、声明/getter及消费者，**没有显式准备writer**。追加common.c没有闭合该关系。平台许可的初始化、完整smp_ops分派、低层启动效果、微码实际行为、所有数量初值/目标覆盖及实际配置仍未证明。不能把静态对象存在、callback返回true或primary成员资格自动当成准备完成；也不能把合法拒绝并行当错误。

因此本例资格状态必须同时携带 `primary_preparation_chain=insufficient`。本轮不继续追writer、APIC、microcode或helper。模型可以保留未知；不能以缺源计算漏检或正常样本。

## F：eligible，但明确为源码接触过的开发试用

父版 `d2e9f53ac5dd76dadc0b5f04f6c27640604ce2af`。**提供者、架构入口和实际公共读端足以形成条件接口问题；不构成独立留出资格。**

- **架构与来源入口**：ARM64 Kconfig132选择generic topology，1384–1405提供MC/CLS/SMT选项；asm头引入公共架构拓扑接口。ARM64 `smp.c:730–734` 在准备CPU时调用init/store；secondary路径243–249先store再notify。公共 `arch_topology.c:826–870` 重置、解析ACPI/DT、尝试缓存信息并store/update；未把未展开helper当成功或把ACPI/DT当两个CPU架构。
- **提供对象**：公共头66–94给出每CPU ID和sibling字段及条件接口。`arch_topology.c:499–682` 的DT解析传递package/cluster/core信息，732–769按缓存、package/cluster/core条件更新相应集合，772–817给出自身位重置/移除。692–729的MC/CLS getter结合节点、LLC与cluster来源选择消费视图；这些ID、raw mask和派生domain span不能混为一份对象。
- **公共实际消费与要求**：调度topology.c:1687–1704的默认层表按配置取SMT/CLS/MC；`sd_init:1589,1628–1629` 实际读取weight并与cpu_map求交。2312–2339对相邻有效span作包含检查/修补，2346–2375要求非重叠同层集合相等或不交。可研究架构/固件提供的视图在所选公共层级是否满足条件，不能将已有检查冒充本项目新机制。
- **关键缺口**：raw源没有实际配置/预处理、具体固件和硬件几何、最终所选层表、完整CPUHP/重建链或缓存helper效果；默认层表可由set_sched_topology更换。所见store早于notify不等于整体数据已正确/完整；空间层级问题也不能硬归为首次准备问题。没有A正常/B暴露运行证据。

## 源码接触与家族

E的公共cpu.c、x86 smpboot/common及接口头在旧版本研究中存在背景接触；本父版的并行启动/primary相关目标机制是否曾参与开发，尚需结合已登记接触记录及解封后的目标范围确定。不能仅同路径一概剔除，也不能因父版/提交hash不同便证明独立。

F的 `cpu_coregroup_mask`、`cpu_clustergroup_mask`、`update_siblings_masks`、`init_cpu_topology`、公共调度层次等关键材料，在旧3fcb研究和本轮D中已经接触；同名定义版本/函数体即使不同，也有明显目标源码重叠风险。**本轮预先按开发型试用处理，不称正式留出。** 是否同故障、同修复家族或另一个目标机制，必须在父版预测/失败/跳过原因保存后再解封子提交裁定；不能仅同文件作家族真值。

## 老师五维分类：父版阶段暂记

| 维度 | E | F |
|---|---|---|
| 触发错误架构 | 未确认错误；源码中有x86_64并行/x86_32分阶段及SMT条件 | 未确认错误；ARM64入口已见，公共体亦含RISC-V条件，未取得RISC-V实际入口或触发 |
| 子系统 | 公共CPU启动/热插拔、x86能力门控与SMT分批 | 公共CPU拓扑/缓存来源、ARM64准备和公共调度域 |
| 横向/纵向 | 架构许可/集合到公共启动算法的纵向接口候选；横向回归未证 | 架构/固件提供到公共拓扑/调度消费者的纵向候选；横向未证 |
| 问题产生侧 | 尚无错误裁定；公共数量/阶段算法与架构许可/集合角色分别记录 | 尚无错误裁定；公共提供/解析逻辑与架构/固件条件联合核查，不按文件目录定罪 |
| 时间线 | 引入、生效、发现及修复均未据父版材料核实；两个目标间隔未知 | 同左；父版hash/源码存在时间不能替代实际出错或发现时间 |

本轮资格eligible只表示值得提出条件候选，不表示任一项为正/正常，不证明检测率、跨架构逃逸或N2增益。保持无新增构建/预处理/内核运行；后续主模型只看中性父版包，不输入本文具体候选要求。
