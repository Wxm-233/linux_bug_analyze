# N2.19 固定父版 I/J 的身份映射与阶段资格复核

本意见仅据 `selection_pre.json`、`protocol_pre.json`、I/J 各 5+3 份固定父版原文、各一次 `symbol_search.json` 和 N2.18 已登记的身份／数量／阶段／映射假说。没有读取 I 的子版提交说明或差分、任何模型回答；没有补采完整文件、编译或运行。J 在选择记录中只是“同用途正常候选”，**不是已经证明的正常真值**；I 的提交题名也不能先验判为缺陷修复。

## I：x86 APIC 物理编号到逻辑 CPU 槽位

`arch/x86/kernel/cpu/topology.c:36–73` 将 `cpuid_to_apicid[逻辑 CPU]` 声明为物理 APIC ID 映射，另用 `phys_cpu_present_map` 记录物理 APIC 呈现；两套编号不能直接比较数值大小或要求相等。`:124–159` 的 `topo_lookup_cpuid` 按 APIC ID 找已有逻辑槽，注释明确映射一经建立应持久；`topo_get_cpunr` 对未知 APIC 从 `nr_assigned_cpus` 分配连续逻辑槽，`topo_set_cpuids` 再把该映射与 possible/present 位写入相同逻辑 CPU 索引。`:192–260` 对真正 present 的 APIC 分配／复用槽位，boot CPU 预留槽位 0，另记录 disabled/rejected；超出 `MAX_LOCAL_APIC` 或早期 `nr_cpu_ids` 的 APIC 可被拒，不能要求所有固件 APIC 都入选。`:268–305` 的 hotplug 路径要求 APIC 先在早期 domain map 登记，再查旧映射或尝试分配槽、设置 present/possible；这里调用的 `topo_assign_cpunr` 在这 8 份文件与有限符号搜索中未见定义，故这一支的完整可编译／可达语义仍未知，不应由助手补造其功能。

数量与阶段须分开：`:317–331` 的早期限制受 `setup_max_cpus`、APIC/IOAPIC 开关和 `possible_cpus` 上限影响，且有 `CONFIG_SMP` 门控；`:334–394` 的 `topology_init_possible_cpus` 在其条件成立时用 assigned+disabled 算 allowed，重设公共 possible/present mask，然后按 **逻辑 CPU 槽位** 0..allowed-1 标 possible；只有槽位有非 `BAD_APICID` 的 APIC，才按 `phys_cpu_present_map` 标 present。因而可有预留 possible 而不 present，不能把 `possible==present` 或“每个 possible 槽在此刻已有真实 APIC ID”作为要求。父版 `arch/x86/include/asm/apic.h:174–197` 同时给出启用本地 APIC 与关闭时的不同声明／空实现。有限搜索只显示 `arch/x86/kernel/setup.c:1134,1146` 调用早期限制和 possible 初始化、`arch/x86/kernel/acpi/boot.c:828` 调用 hotplug 接口；这些不是两文件完整调用体，不能据此认证全部固件枚举顺序或激活配置。

现有接口义务的保守表述是：在明确选择域和阶段内，被接受的物理 APIC 身份应通过版本化映射关联到稳定且容量内的逻辑 CPU 槽；公共 mask 的位表示**逻辑** CPU，不是原始 APIC ID；possible 可包括合法预留槽而 present 只反映对应阶段已呈现的槽。`include/linux/cpumask.h:5–8,90–105,993–1027` 及 `kernel/cpu.c:1912–1919` 支持公共逐位身份语义，并显示通用 bringup 的串行分支以 present mask 为输入；`kernel/smp.c:934–989` 区分早期 `nr_cpus` 限额、`maxcpus` 激活额及之后 `setup_nr_cpu_ids` 的最高 possible 位边界。固定包没有合法 `.config`、实际 APIC/ACPI 枚举、`topo_assign_cpunr` 实现、真实 hotplug 调用或运行结果，所以不能证明 I 父版违约、这是新 bug、也不能把旧 SPARC 的 raw-ID 子集规则直接套上来。既有接触记录还披露过 `arch/x86/kernel/cpu/topology.c` 同路径旧版本整段源码；目标函数重叠与修复家族目前未核清，独立资格为**待定**，不是“hash 未命中即未读”。

## J：PowerPC 的 OF 硬件 ID 映射与 possible 预留

`arch/powerpc/kernel/setup-common.c:414–430,432–486` 明确在 OF、`finish_device_tree` 已完成的前提下建立 possible/present：顺次给设备树线程分配逻辑 `cpu` 槽位，按设备节点可用性设置 present，possible 对已分配槽置位，并将 `ibm,ppc-interrupt-server#s`／`reg` 转换出的物理 ID 记入 `cpu_to_phys_id[cpu]`。缺少该属性时源码有“assume logical == phys”退路（`:460–465`），所以物理＝逻辑仅是这一个受限分支的假设，非跨架构规范。`nr_cpu_ids` 限制循环分配数量（`:469–492`）。在 `CONFIG_PPC64` 且 `FW_FEATURE_LPAR`、`/rtas` 与 `ibm,lrdr-capacity` 有效时，`:500–539` 进一步把额度内的逻辑槽标 possible，**没有同步标 present 或给每个预留槽赋真实硬件 ID**。这正是需要保留的合法候选形状；但固件条件及后续物理 ID 赋值实际满足与否尚未证明，不能据此宣布整条 J 路径正常。

`setup-common.c:550–551,860–874,923–945` 显示 possible 构造后重算 `nr_cpu_ids`，随后按 possible 预备 PACA／硬件 ID 表并释放临时 `cpu_to_phys_id`。对**预留**槽，当前包没有证明这一暂存表项已含有效硬件 ID；不得把 `smp_setup_pacas` 的写入等同于真实设备映射已完成。`arch/powerpc/include/asm/smp.h:87–105,209–230` 还按 PPC64/PPC32、SMP/非 SMP 给出不同存放方式，当前不应混用。公共 `kernel/cpu.c:1912–1919` 的初始 bringup 串行分支只按 present mask；PowerPC `arch/powerpc/kernel/smp.c:1092–1127` 对 possible 槽做资源准备，`:1270–1353` 的 `__cpu_up` 依赖平台回调并等待 online。这说明 J 承担与 I 相同的**向公共 CPU 集合提供逻辑身份、再进入公共 bringup** 用途，但它的合法空间包含预留 possible、未 present、暂未绑定现存硬件 ID 的阶段。没有实际平台回调、设备树、配置和热插拔全链，本包不能确认预留槽最后何时成为 present/online，也不能把“无报错”或“功能关闭”充作正常证明。

## 对本轮父版模型分析的准入与缺口

两份父版材料都足以进行**一次有条件的源码候选分析**：比较各自的物理→逻辑映射、选择／限额、possible/present 的阶段角色，并指出公共消费使用逻辑索引；J 可以检验“原始物理编号必须等于 mask 位”与“全部 possible 当前必须 present”这两种过强说法。材料并不足以给 I 阳性或 J 阴性真值，也不足以正式证明独立检测：I 同路径旧源码接触与家族未知、J 仅有限记录无命中；两组实际配置、完整枚举／hotplug 提供者、设备运行均缺失。模型若给不出映射对象或阶段，或程序不支持这些事实，应保留原定对象与不足，不凭修复或结果换例。I 子版修复和历史目的性解释必须等父版候选／失败保存后再开放给独立 oracle。
