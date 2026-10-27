# N2.17 修复依据与研究范围复核（研究侧）

本意见只使用事先固定的 G/H 各 8 份父版源码、`protocol_pre.json`／`selection_pre.json` 以及在父版预测和检查记录保存后开放的 `repair_evidence.json`。没有查看两项模型原答或 `candidate_checks`，也没有新增源码、配置或运行实验。**隔离限制：**主任务在我落盘前提示了 G 的“稀疏 CPU 编号被 dense prefix 重写”边界；因此本文虽未接触模型输出，却不是完全不受受测候选影响的盲态语义 oracle，应标为“受主任务提示的研究侧边界复核”。提交说明是作者／报告者的陈述，不等于本轮复现或独立规范。

## G：SPARC64 的 CPU 身份集合

**实际修复及依据。**父版 `arch/sparc/kernel/prom_64.c:434–465,481–498` 从 OF CPU 节点取得实际 `cpuid`，在 `record_one_cpu` 将它加入 present、possible 集合；随后 `arch/sparc/kernel/setup_64.c:669–680` 调用 `smp_fill_in_cpu_possible_map`。该父版函数以 `num_possible_cpus()` 得到**数量**，再把 possible 位重写为 `[0, min(数量,nr_cpu_ids))` 的连续前缀，清掉余位（`arch/sparc/kernel/smp_64.c:1219–1231`）。若被选择的 CPU 身份为非连续编号，数量无法代替编号集合，重写可丢失真实 ID 并加入不存在的 ID。修复将 `num_possible_cpus() < nr_cpu_ids` 的**名额判断**移到 `record_one_cpu` 设置 possible 位之前，删除后续连续前缀重写及其声明／调用；present 设置仍保留。修复没有要求“所有 present CPU 必须 possible”，尤其不能把存在启动数量限制时被跳过的 CPU 算作违约。`include/linux/cpumask.h:5–8,90–105,1004–1032,1114` 明确 mask 逐 CPU 编号占一位、possible 表示可被启用的身份集合、`for_each_possible_cpu` 遍历实际位、`num_possible_cpus` 只是集合大小；这是比提交标题“online CPUs”更直接的现有接口依据。固定材料没有展开启动参数解析、每次枚举顺序与当时 `nr_cpu_ids` 的具体值；不可据此宣称任意配置下修复均保证每个探测 ID 合法，或把所有 present 都强制纳入 possible。

**跨层传播与暴露。**架构侧的 OF `cpuid` 可以稀疏，而共享 cpumask API 按身份位解释 possible；SPARC 父版转换把“数量”误当“编号前缀”。本包显示 `arch/sparc/kernel/setup_64.c:602–619` 的 IRQ 栈分配以及 `arch/sparc/kernel/smp_64.c:1570–1579` 的 per-CPU 偏移初始化都按 `for_each_possible_cpu` 消费，故可证源级错误集合会传给这些消费点；`arch/sparc/kernel/smp_64.c:1283–1301` 的启动等待与 `kernel/cpu.c:1908–1916` 的通用 bringup 展示后续在线过程，但这 8 份文件不足以把特定丢失位与报告机器上“CPU 2 未上线”连成完整运行因果链。提交说明报告双 CPU Ultra 60 上只有 CPU 0 启动、CPU 编号 0/2，且声称回退有效；本轮没有相应硬件、启动配置或运行观测。ARM64 同版父源码 `arch/arm64/kernel/smp.c:483–500,679–715` 是先形成逻辑 CPU 映射、初始化成功后按逻辑编号设置 possible 的不同提供路径，支持“架构提供方式不同、公共集合接口相同”的源级对照；它此前已整文件曝光，且尚未建立同用途正常配置／启动真值，不能充当独立正常对照。

**范围与资格。**G 是“架构特有 CPU 编号表示 → 公共身份集合契约 → 按集合位消费”的**核心范围候选**，错误发生在架构侧的准备／改写，公共接口语义本身未见被修复修改。当前有限接触索引未发现这个 hash 或目标 SPARC 源码先前用于方法开发；但 500 条初筛标题已接触，家族与全局未接触并未证明。故只可称“在已检查记录下没有发现目标位置泄漏的待评价候选”，不能称严格未见样本或独立成功检出。若后续资格确认但父版材料、配置或当前程序语法仍不足，须作为 G 的**不足结果留在预定评价分母**，不可按工具支持性剔除或补选。

## H：x86 混合 CPU 的调度拓扑选择

**实际修复及依据。**父版 `arch/x86/kernel/smpboot.c:569–594` 的 x86 拓扑在 `CONFIG_SCHED_CLUSTER` 下加入 CLS 层；`cpu_clustergroup_mask` 返回 L2 共享集合（同文件 `:682–691`），核心／SMT 层另有各自 mask 和 flags。启动路径先选 x86 默认拓扑，NUMA-in-package 情况改选相应拓扑（`:1374–1383,1466–1477`），父版没有 hybrid 特殊分支。修复新增不含 CLS 的 `x86_hybrid_topology`（保留配置允许的 SMT、MC、DIE），并在 `native_smp_cpus_done` 的 NUMA 分支之后以 `X86_FEATURE_HYBRID_CPU` 门控选择；`arch/x86/include/asm/cpufeatures.h:386` 将该特性描述为多种 CPU 类型。`include/linux/sched/topology.h:193–204` 与 `kernel/sched/topology.c:1633–1664,2208–2228` 说明架构传入拓扑层数组、公共调度域构建器遍历各层；`:1538–1544` 确认 mask 和 flags 被消费。提交说明主张混合 CPU 的选择应按优先级、CLS 可能使 Atom 群偏重；这是该修复引入的**条件性策略依据**，并非固定父版中的普适 ABI 定理或本轮实测调度偏差。

**传播、差异与边界。**可证链是“x86 CPU 型号／能力差异 → 架构选择含或不含 CLS 的拓扑数组 → 公共 scheduler 构建不同域”；固定材料没有完整任务选择路径、Alder Lake 实际特性与配置、调度测量，也没有同用途另一 ISA 的合法对照。修复仍保留普通 x86 的 CLS，且依赖 `CONFIG_SCHED_CLUSTER`、HYBRID 特性与启动顺序；新增注释暂假定 NUMA-in-package 与 hybrid 不重叠，不能推成已证明所有模式的优先级。H 更适合**辅助机制／开发迁移**：它是同一 x86 ISA 内不同 CPU 型号的策略适用性问题，不能作为严格跨 CPU 架构的独立核心正例来增加计数。旧接触索引虽未命中此 hash，但 `arch/x86/kernel/smpboot.c` 整文件及 cluster 提供相关位置曾在方法开发中读过；已登记 `not_independent_of_method_development`，不因修复补丁与旧例 hash 不同而恢复独立资格；“同修复家族”也不能仅凭同文件／主题断言。

## 本轮可报告层级

两项都能从固定父版与修复差分解释源级机制；G 的硬件启动因果、H 的实际调度偏差、适用配置及跨架构正常对照均未由本包验证。本文是修复揭示后的研究者范围复核，不是模型自动提取成效，也不用于回填父版预测或更换样本。G 可进入预定核心候选评价并保留不足，H 只能另列已读开发／辅助观察；ARM64 正常候选目前不能作为独立已证正常。
