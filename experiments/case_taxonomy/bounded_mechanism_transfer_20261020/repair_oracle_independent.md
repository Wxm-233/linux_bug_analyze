# G/H 历史修复独立范围审阅

本审阅只读取本目录的 `selection_pre.json`、`protocol_pre.json`、`evaluation_scope_pre.md`、`contact_review_pre.json`、`documents_G.json`、`documents_H.json` 与 `repair_evidence.json`。源码引用均指后两份 documents JSON 内固定父版的 `documents[].text`，行号按原文换行计数。本审阅未读取模型目录、模型回答或预测、`candidate_checks`、其他角色报告、README、主任务结果及上述文件所引用的其他文件；没有采集新源、调用外部模型、编译、预处理或启动系统。以下判断先于任何预测比较保存。

## 判定口径

分开判定四件事：历史问题是否有证据、架构提供者是否影响公共用途、是否属于本项目当前两条具体机制、是否可计独立评价。历史补丁与 Tested-by 是已有修复证据，不等于本轮独立运行复现；源码条件推演也不等于实际合法配置与路径已观测。解析工具能否处理源码不影响前述资格。

本次允许材料没有包含此前两条机制的完整契约和判定协议，故对“同机制”的判断限于任务给定的 N1“首次消费前的语义准备”与 N2“来源/导出”描述，不自行把它们扩成所有架构初始化或所有数据传递。可以确认更广的研究相关性，同时保留具体机制不一致或尚未证的结论。

## G：稀疏 CPU ID 在 possible mask 整理时被替换

固定父版：`95706e717c4f55ca62025c151451ccc28863d085`；修复：`98937707fea8375e8acea0aaa0b68a956dd52719`。

### 事实与因果链

1. G/D02 `arch/sparc/kernel/prom_64.c:435–467` 从设备树 CPU 节点读取 `mid_prop` 或 `cpuid`，在 SMP 下排除 `cpuid >= NR_CPUS` 后，将实际 ID 传给回调。`record_one_cpu:481–488` 同时执行 `set_cpu_present(cpuid, true)` 与 `set_cpu_possible(cpuid, true)`。`of_populate_present_mask:491–498` 对非 hypervisor 路径执行枚举。因此此路径把固件给出的 ID 直接用作公共 cpumask 的位索引，没有在这里重新压成连续逻辑 ID。
2. G/D04 `arch/sparc/kernel/smp_64.c:1219–1231` 先取 `num_possible_cpus()` 得到集合基数，再将 `[0, min(基数, nr_cpu_ids))` 置真、其余到 `NR_CPUS` 置假。G/D05 `include/linux/cpumask.h:699–707,1114` 明确该量是置位数，不能据此恢复原集合成员。源集合的基数等于 2 并不意味着其成员为 0、1。
3. 一个有明确条件的源码推演是：SMP、非 hypervisor、固件有效 ID 为 `{0,2}`、`NR_CPUS > 2`，且计数时的有效位范围包含 CPU2、`nr_cpu_ids >= 3`。枚举后 present/possible 均含 0、2；旧整理函数将 possible 改为 `{0,1}`，present 仍含 0、2。这里的错误是丢掉真实成员 2 并添加没有枚举出的成员 1，而非仅在线数量显示错误。此推演条件没有作为本轮实测配置。
4. G/D05 `include/linux/cpumask.h:90–113` 对公共接口的既有含义有明确说明：possible 位对应可存在的 CPU ID，present 位对应已存在的 CPU，online 是可用于调度的 present 子集。G/D06 `kernel/cpu.c:1735–1743` 的公共 `cpu_up()` 在 `!cpu_possible(cpu)` 时直接返回 `-EINVAL`；`cpuhp_bringup_mask:1818–1838` 调用它，`bringup_nonboot_cpus:1908–1915` 的串行路径以 present mask 为输入。这使错误架构输出能够进入公共 CPU 上线用途，不只是架构私有显示。
5. G/D03 `arch/sparc/kernel/setup_64.c:672–680` 在调用旧整理函数后调用 `alloc_irqstack_bootmem()`；该函数 `602–619` 遍历 possible CPU 分配 IRQ 栈。这另证错误成员集合会被真实初始化用途消费，但本轮不据此增报另一项实际故障，也不把这个局部调用认作全系统首次消费已证明。
6. 修复正文报告 Ultra 60 两个 CPU 的 ID 为 CPU0、CPU2，回归始于 `9b2f753ec237`，撤销旧改动可恢复两 CPU，且补丁有报告者 Tested-by。diff 删除后续连续化函数与调用，在 `record_one_cpu()` 中按 `num_possible_cpus() < nr_cpu_ids` 的数量限额决定是否保留实际 `cpuid`。它改变的是限额施加位置，并保留实际 ID，不是后来新设一项公共 CPU 编号政策。

### 范围结论

- **历史真实问题：有力支持。** 补丁报告、定位/撤销反馈、测试署名与父版条件推演互相吻合；本轮没有独立复现历史机器。
- **既有接口义务：支持。** 义务是向公共 CPU mask 保留被选中可用 CPU 的身份，并正确施加数量限制；不能用“基数相同”替代成员正确。不能从标题把 `online` 与 `possible` 混称。
- **广义 CPU 跨 ISA 核心相关性：支持。** SPARC 使用固件 CPU ID 作位索引，而同版 ARM64 另建硬件 ID→逻辑 ID 映射；差异通过相同公共 possible/present/上线用途暴露。稀疏 ID 与 SMP/平台是触发条件，不能因此将它降为纯型号调优或架构内部输出。它是一个合格的源码语义层跨架构接口候选。
- **与当前具体机制：集合身份保持/数量限额转换是这里的直接机制。** 父版已做枚举并准备 mask，随后又以错误转换破坏内容；这不等同于仅验证“首次使用前是否发生某准备事件”。也没有证据表明错误根源是来源不明、选错权威源或缺少某导出操作。若 N1 的“语义准备”允许推导集合成员正确性，或 N2 的“来源/导出”允许验证源集合到公共表示的成员保持，本例可成为扩展挑战；但必须事前定义这种契约及语义判定，不能只凭事件顺序/引用绑定就把它算两条已冻结具体机制的同类成功。就允许材料而言，严格同机制适格性尚未证明；广义接口候选资格成立。
- **材料缺口不改变候选资格。** 允许父版没有提供 `paging_init()` 内到 `of_populate_present_mask()` 的完整调用段、`nr_cpus` 解析与最终 `nr_cpu_ids` 确定链、具体 `.config`/设备树/启动记录，也没有本轮内容消费观测。因此可确认局部错误变换及公共拒绝条件，不能声称本轮配置可执行性、全启动链与实际线上违约均已验证。hypervisor 路径还需另查；不能把这项非 hypervisor 问题泛化到所有 SPARC64。

### ARM64 固定正常候选

G/D07 `arch/arm64/kernel/smp.c:621–675` 将硬件 MPIDR 放入 `cpu_logical_map(cpu_count)`，不是把稀疏硬件编号直接当作公共 mask 的位；`smp_init_cpus:684–714` 在逻辑 ID 范围内初始化，`smp_cpu_setup:483–501` 仅在 CPU 操作初始化成功后设置 possible；`smp_prepare_cpus:717–760` 遍历 possible，并在 `cpu_prepare` 成功后设置 present。G/D08 `arch/arm64/include/asm/smp.h:45–62` 也明确逻辑映射及发现 possible CPU 的用途。因此，**同用途的源码比较成立**，可解释为何不能要求两架构逐行相同或都保留硬件编号。

这不足以给 ARM64 实现整体打正常真值。未给出实际合法活动配置、对应固件输入、外部 CPU 操作的成功保证及完整调用链；`max_cpus == 0` 还是有意不设置 secondary present 的分支，不能把禁用路径当正常对照。接触记录明确同一实现整文件先前已用于开发 F，故 **不计独立正常留出**。目前可作已接触的、条件性的同用途源码参照；“没有发现同类坏转换”不等于正常保证。

## H：混合 x86 CPU 的调度拓扑策略不兼容

固定父版：`0fcfb00b28c0b7884635dacf38e46d60bf3d4eb1`；修复：`cabdc3a8475b918e55744f43719b26a82dc8fa6b`。

### 事实与因果链

1. H/D01 `arch/x86/kernel/smpboot.c:469–481,603–639` 根据 L2 cache ID 建立共享 mask；`cpu_clustergroup_mask:688–691` 导出该 mask。H/D05 `arch/x86/kernel/cpu/cacheinfo.c:761–764,845–850` 显示 L2 ID 从缓存共享信息得到并写入 `cpu_l2c_id`。这是有来源的缓存拓扑，不是证据显示缓存关系本身造假。
2. H/D01 `x86_topology:582–594` 在 `CONFIG_SCHED_CLUSTER` 下包含 CLS 层；`x86_numa_in_package_topology:569–580` 也包含 CLS。默认 x86 拓扑在 `1381` 交给 `set_sched_topology()`；旧 `native_smp_cpus_done:1466–1478` 仅可能改选 numa-in-package 版本，没有混合 CPU 专用拓扑。
3. H/D03 `include/linux/sched/topology.h:193–204` 定义公共拓扑回调；H/D04 `kernel/sched/topology.c:1658–1664` 保存架构数组，`sd_init:1538–1544,1577–1585` 调用其 mask/flags 构建调度域，`2208–2227` 遍历选定层级。H/D08 `Documentation/scheduler/sched-domains.rst:29–53,72–74` 说明公共负载均衡按这些域/组工作，也允许架构经此 API 覆盖拓扑。因此 H 确属架构提供者影响公共调度用途，不能仅称架构内部数据。
4. 父版已有 CPU 优先级接口：H/D02 `arch/x86/include/asm/topology.h:169–182` 声明 ITMT 及 core priority 设置；H/D01 `544–565` 在 ITMT 启用时给 SMT/CLS/MC 加 `SD_ASYM_PACKING`；H/D04 `1238–1277` 说明组 capacity 影响负载分配，并以 `sched_asym_prefer()` 选择组内优先 CPU。H/D04 `1499–1519` 也区分拓扑描述与映射出的行为，不能将一个真实的共享缓存 mask 自动视为适合所有调度政策。
5. 修复正文明确要求 hybrid CPU 按 CPU priority 选择，指出 Alder Lake 的 4 Atom cluster 与 2 hyperthread Big core cluster 容量差可能偏向 Atom，给出 Fixes 与 Tested-by。diff 新增仅含 SMT/MC/DIE、没有 CLS 的 `x86_hybrid_topology`，在 `X86_FEATURE_HYBRID_CPU` 为真时覆盖拓扑选择；H/D07 `arch/x86/include/asm/cpufeatures.h:386` 将该特性定义为含不止一种 CPU 类型。修复仍保留缓存关系的提供者，改变其是否作为调度域层级使用。

### 范围结论

- **历史真实问题：支持其为已有回归/策略不兼容修复。** 不应因正文使用“could potentially”而当作已观测到具体性能损失；此轮也没有任务轨迹或性能结果。Tested-by 不是本轮独立效果量。
- **既有要求与规范来源：部分支持。** 父版确有优先级/非对称调度机制；混合 CPU 必须严格按优先级、CLS 不得干扰的具体政策由本次修复正文明确。仅凭这些父版片段无法独立推出“所有 hybrid 组合必须禁 CLS”，也不能将后来新增分支当作先验规范已经自动推导成功。
- **广义架构→公共接口相关性：成立；CPU 跨 ISA 核心样本：不成立。** 这次因果差异在同一 x86 ISA 内的混合 CPU 类型、缓存组大小和调度配置，不是已展示的跨 ISA 接口缺失。适合作为配置/型号条件下的辅助源码案例或外部机制挑战；这不撤销它已经参加父版试验的事实。
- **具体机制不同。** 拓扑与 mask 已准备并导出，有真实缓存来源，公共调度器也按接口使用。问题在于对特定硬件模式选用哪一层拓扑，及拓扑组容量与 CPU priority 两种策略的相互作用，既不是缺少首次消费前准备，也不是已经证明的来源/导出遗漏。要覆盖它，需要硬件模式限定的策略兼容契约与任务选择/负载行为判据；把 `HYBRID_CPU` 分支或新补丁结论补入后再称既有两机制验证，会泄漏答案。
- **关键缺口：** 允许材料没有实际 `.config`、HYBRID 特性启用链、ITMT 优先级赋值/启用的实现和轨迹、`sched_asym_prefer()` 与实际任务选择/组间负载决策实现及运行观测。没有证明本轮某一配置确实选到低优先级 CPU，也没有证明所有 hybrid、SMT、MC、NUMA-in-package 组合的政策覆盖。新 diff 中关于 hybrid 与 numa-in-package 不重叠的注释本身也不能充当配置合法性证明。

## 接触、家族与评价分母

| 对象 | 本次来源与范围判断 | 独立性结论 | 可保留的评价位置 |
| --- | --- | --- | --- |
| G | 合格的跨架构公共 CPU 集合语义候选；严格当前两机制同类资格尚未证 | 目标位置在已做的有界开发记录搜索未命中；不能据此证明全局未读，也不能反过来据此认定开发已读。Fixes 指向 `9b2f753ec237`，但允许接触材料未完成与既有开发案例的修复家族隔离 | 保留本次候选、固定父版试验、材料覆盖及工具支持分母；可作潜在独立的外部机制挑战，暂不计正式独立同机制成功/失败率 |
| H | 公共调度用途成立；同 ISA 型号/配置策略辅助，非已证当前两机制同类 | 目标文件与 cluster 提供者已有方法开发接触，明确非独立；相同修复家族关系仍未证 | 保留本次候选/父版试验和开发迁移结果，不计独立留出 |
| ARM64 参照 | 源码上同公共 possible/present/上线用途成立；整体正常保证未证 | 同一实现文件先前已用于开发，明确非独立正常留出 | 仅作条件性源码参照，不进入独立正常真值分母 |

两项手工定向选择、两项固定父版尝试始终保留，不能在看到预测或解析结果后补选或删除。本审阅不读取工具输出来改判资格。G 的语义候选资格与 H 的公共用途成立，说明这次尝试有可报告的研究覆盖边界；严格当前机制和正式独立样本不足，也不能据此把全部尝试抹成没有评价对象。若需要计“同机制”或独立留出的统计，须先完成相应契约边界/修复家族核对，并按已冻结规则处理，不能用模型是否答对来决定。

本文件未评价受测模型预测、工具命中率、完整普通模型基线、自动化增益或新缺陷发现。比较预测应以本文件保存后的单独阶段进行，并明确区分父版自动产物、人工角色/规范输入与本次后验修复知识。
