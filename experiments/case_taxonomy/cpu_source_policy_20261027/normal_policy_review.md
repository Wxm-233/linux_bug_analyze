# 同上下文默认实现的正常用途资格

2026-10-27；研究者源码审核，不是模型自动推导或独立金标准。

对象限定为本轮已固定的 old_s390、fixed_s390 两个 SMP/SYSFS/NR_CPUS=4 编译上下文，及公共 topology 属性组的 package、core 用途。die 的成组原生来源政策不自动迁移到这些用途。

两个版本 Documentation/admin-guide/cputopology.rst 均说明公共 driver 导出拓扑属性，公共头提供架构未定义项的默认值：physical_package_id=-1、core_id=0、sibling_cpumask/core_cpumask 为给定 CPU。原/修复文件分别见 policy_sources/manifest.json；修复文档另明确 die 层级的架构提供者条件。

同版 drivers/base/topology.c 将 physical_package_id + package_cpus/package_cpus_list，以及 core_id + core_cpus/core_cpus_list 接入公共属性表；分别消费 physical_package_id/core_cpumask、core_id/sibling_cpumask。这里不是根据属性名称猜 mask：core_cpus 对应 sibling_cpumask，package_cpus 对应 core_cpumask。

本轮要求仅为“已选择导出的上述属性组，其两个有效提供者均符合该用途已审核的来源许可”：provider_ok = reviewed_native OR documented_default_permitted。默认实现必须同时有准确的宏体、来源、当前上下文及实际展开/表项证据，不能只见 fallback 字样便通过。

本轮两配置中这四个宏都来自 include/linux/topology.h 的默认定义；展开后的 ID 函数得到 -1/0，mask 函数调用 get_cpu_mask(dev->id)。此为同一已读案例中的文档默认政策和源码导出一致性控制，不证明物理拓扑真实、运行时值已准备、实际文件已创建或所有用途都允许默认值。四个“配置×用途”是源码对照单位，不是四个新案例或独立正常样本。

契约关系和用途许可仍由研究者登记；程序抽取有效来源、展开位置及完整属性表，并交给不变的 contract_protocol.py。normal_policy.json 内的许可若用于 die 组、其他版本/配置/未知宏体，应拒判，不能把这些默认许可当通用豁免。
