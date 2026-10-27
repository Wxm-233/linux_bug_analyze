# N2.19 I 的修复开放后独立范围判读

仅使用固定的 `selection_pre.json`、`protocol_pre.json`、`documents_I.json`／`documents_J.json`、已落盘 `parent_scope_review.md` 和在 I/J 父版 attempt/checkpoint 保存后开放的 `repair_evidence.json`。写本意见前**没有阅读**本轮模型 final、`candidate_checks`、`parent_prediction_audit` 或比较结论；没有增加父版 8 文件以外的完整源码、构建或运行。修复提交说明是作者意图和历史记录，不等于本轮独立重现或接口规范。

## I 实际修改了什么

父版 `arch/x86/kernel/cpu/topology.c:36–73,124–159` 把逻辑 CPU 号映射到物理 APIC ID；对已 present 的 APIC，`:192–210` 在早期登记逻辑号和映射，而对登记但未 present 的 APIC，父版先只增加 `nr_disabled_cpus` 并把 APIC 加入 domain map（`:210–216`）。父版 `topology_init_possible_cpus:350–394` 计算 assigned、disabled 与 allowed，可能留下已标 possible、但 `cpuid_to_apicid` 仍为 `BAD_APICID` 的逻辑槽。父版 `topology_hotplug_apic:268–289` 在物理 hotplug 时查映射，不存在时打算检查名额并再分配逻辑号。这个“稍后分配”路径是父版设计形状；固定父版材料与一次有限符号搜索没有给出 `topo_assign_cpunr` 定义，故不能认证那条路径实际构建、运行或返回行为。

I 子版差分所能确认的变化是**把非 present APIC 的逻辑号绑定提前到初始化**：在 `topology_init_possible_cpus` 重新算出的 `disabled=allowed-assigned` 范围内，用 `find_next_andnot_bit(已登记 SMT APIC map, phys_cpu_present_map, MAX_LOCAL_APIC, ...)` 依 APIC ID 扫描未 present 但已登记的条目，写入 `cpuid_to_apicid[topo_info.nr_assigned_cpus++]`；然后原有的 allowed 逻辑槽循环仍设置 possible，仅映射到物理 present APIC 的槽才标 present。对子版已 present 的早期登记，映射写入从通用 `topo_set_cpuids` 移到 `topo_register_apic` 的 present 分支；hotplug 不再临时分配新逻辑号，查不到已登记映射则返回 `-ENOSPC`。随之 `cpuid_to_apicid`、`topo_info` 改为 `__ro_after_init`，`topo_get_cpunr` 改为 `__init`。这是一组**绑定时机和数据生命周期策略**的协调修改，不能只摘掉 hotplug 分配一行就称完整修复。差分未显示修改通用 cpumask 或公共 bringup 语义。

## 权威依据、机制链与研究范围

父版已有的接口事实是 `cpuid_to_apicid[逻辑 CPU]` 映射到物理 APIC ID，且 `topo_lookup_cpuid` 注释强调映射一旦建立即保持；公共 `cpumask` 一位对应一个**逻辑** CPU，通用 `kernel/cpu.c:1912–1919` 的串行 bringup 以 present mask 选当前可启动对象。它们支持按逻辑槽核身份、容量与阶段，却**不要求**每个 possible 槽在初始时有现实硬件，也没有规定 non-present APIC 必须在 init 而非 hotplug 时分配逻辑号。后者是 I 子版明确采用的新策略及 `__ro_after_init` 的前提；不能把子版政策追认成父版已违反的既有 ABI。父版 hotplug 后一旦分配，仍可满足“映射建立后持久”的较弱义务；本包没有展示父版发生重复号、错误 APIC 绑定、公共消费错误或 CPU 启动失败。

可描述的跨层关系是：x86 提供者掌握物理 APIC 集合，依据早期/后期策略给其中的 CPU 建立逻辑编号，并将 possible/present 作为逻辑位交给公共 CPU 生命周期代码；I 子版改变 non-present 但已登记 APIC 的**映射准备期限**，使以后该 APIC 变 present 时可沿预先固定的逻辑槽更新。适用边界同时依赖 `CONFIG_SMP`、本地 APIC、热插拔分支、早期上限与 `possible_cpus` 参数、disabled APIC 的登记方式以及实际固件顺序。固定 8 文件只通过有限 grep 显示 x86 setup 和 ACPI 调用位置，没有它们完整正文；也无真实 `.config`、设备、构建和 hotplug 观测。`find_next_andnot_bit` 的命中是否完整覆盖给定固件及真实机器不能从提交说明或此包推定。

提交题名和说明写的是“在初始化时给 hotpluggable CPU 分配编号”，理由是无需等物理 hotplug 才编号、可把更多代码设为 `__init`、相关数据设为 `__ro_after_init`；没有 `Fixes:`、明确旧版错误输出、复现条件或用户可见症状。故当前最稳妥的裁定是**功能／生命周期策略调整，缺陷修复证据不足**；不能把“某个旧 helper 未见定义”自动归为运行 bug，也不能在见修复后为了样本阳性改写研究范围。I 是预选一次条件分析对象，其结果无论程序支持与否均保留；但若研究统计只计“已确认跨架构缺陷”，I 目前不能充作新的阳性或独立有效检出。选例记录还披露 x86 同一路径旧版本源码曾曝光，具体目标位置重叠和同家族关系仍不明，独立性同样不可宣称。

## J 参照的正常性边界

同父版 PowerPC `arch/powerpc/kernel/setup-common.c:432–486` 将 OF 线程硬件 ID 映射到逻辑 `cpu`，为已枚举槽设置 possible，并按设备可用条件设置 present。`CONFIG_PPC64` 的 LPAR/RTAS 容量分支 `:500–539` 可再预留 possible 槽，而当前没有同步 present 位或逐槽可信物理 ID；之后 `smp_setup_pacas:860–874` 会处理 possible 槽，实际未呈现槽的硬件 ID 何时绑定仍缺完整路径与配置。J 与 I 同为“架构把硬件身份映射为公共逻辑 CPU 集合”用途，但**允许 possible 预留而未 present**，也不要求 raw 硬件 ID 与逻辑位相等。这可反驳过强的通用谓词，却不足以证明 J 在任何实际平台正常运行；没有同用途的独立真值或修复对照。不能为了让 I 显得是 bug 而把 J 预留槽当异常，也不能为了让 J 看似正常而忽略其映射来源缺口。

本意见是修复已开放后的人工源码范围裁定，不是模型自动提出要求、程序通过验证或跨架构泛化成绩；正式比较须在保留父版原候选／检查记录不变的前提下，单独对照它们是否真的说到了映射对象、选择域和期限。
