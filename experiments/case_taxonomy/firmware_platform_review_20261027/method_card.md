# 固件与平台信息接口：限定方法卡

2026-10-27。范围为已读开发材料：ACPI MADT LAPIC/x2APIC记录接受（aa06e20f1be6→e2869bd7af60→a74fabfbd1b7→fed8d8773b8e→adbf61cc47cb历史链）及其真实环境覆盖，Xen PV DomU早期平台判断导致的CPU范围收窄（父`0af2f6be`/修复`8b37357a`）。本卡完成**限定开发方法阶段评审**，不是整个固件/平台家族、裸机/厂商固件验证、自动推导或独立评价完成。提纲按《最终研究目标与阶段推进原则》八项。

## 1. 消费用途与判定依据

固件/平台提供的信息被公共层当作**是否接纳某个CPU、可接纳多少CPU**的依据：

- ACPI：MADT每条LAPIC/x2APIC记录经`acpi_is_processor_usable()`决定是否注册为可能CPU，进而决定possible/present、热插槽与`cpuid_to_apicid`；热插时ACPI处理器路径需要为新CPU映射逻辑编号。
- Xen：早期`acpi_mps_check`等平台判断可先把`nr_cpu_ids`压低，随后PV提供者按已收窄的上限枚举。

依据分三类，权威强度不同，研究者负责登记与版本：ACPI规范（6.3引入Online Capable；此前Enabled=0表示不可用）；Linux兼容政策（QEMU用Enabled=0表示热插槽，`adbf61cc47cb`说明“只对guest允许”）；具体实现事实（识别表、`nopv`、setter赋值分支）。政策不是规范，不能互相替代。

## 2. 适用条件与目标关系

| 维度 | 取值 | 不显式会怎样 |
| --- | --- | --- |
| 固件能力版本 | FADT≥6.3或MADT rev≥5 才有Online Capable语义；QEMU 8.2.2实际为FADT/APIC v03 | 把规范新语义套到旧表会误判 |
| 兼容政策作用域 | guest（按政策意图）vs 裸机（按规范） | 不分作用域会两头出错（历史上分别破坏QEMU与裸机） |
| 环境分类来源 | 内核识别到的hypervisor类型（kvm需KVM_GUEST，可被`nopv`关闭；TCG不在识别表） | 把“识别到hypervisor”当成“是guest”，实测TCG/nopv guest失去热插槽 |
| 记录类型 | LAPIC vs x2APIC | 历史修复曾只改其中一条路径 |
| 阶段 | 早期平台判断→限额→提供者枚举→后期例外 | 后期例外不能恢复已截断的枚举（Xen） |
| setter赋值分支 | 可赋值 vs FORCE/NR_CPUS==1只告警 | 按函数名推断“已限额”过强 |

目标关系：A1接受决定与版本化能力一致；A2兼容政策只在其作用域内放宽；A3（新）政策作用域条件的提供者须覆盖政策意图的环境——P1“依赖legacy热插槽的QEMU guest启动possible≥present+热插槽”；A4热插上线CPU属于启动possible（P3）；X1早期范围不应因不适用的平台判断被收窄。

## 3. 提供者保证

- 固件（QEMU）：同一配置在KVM/TCG下生成完全相同的MADT（0x90、v03）与FADT（v03），热插槽为Enabled=0条目；QEMU接受QMP热插请求，但Linux是否能用取决于启动时possible。
- 内核环境分类：`init_hypervisor_platform`在`acpi_boot_init`与`topology_init_possible_cpus`之前执行，阶段可用；但只提供“已识别类型”，不提供“是否guest”。
- Xen：PV DomU选择提供者，实际APIC接受/去重/映射未投影。

## 4. 事实与证据层级

| 层级 | 已有 | 证明到哪里 |
| --- | --- | --- |
| 宿主原函数投影 | ACPI 6修订×52例=312条；Xen 12条件对（24记录） | 显式政策下各修订接受/能力差异；早期收窄不被后期恢复 |
| 编译器事实 | setter三分支GIMPLE写入 | FORCE/NR_CPUS==1不赋值 |
| 真实内核+注入固件 | 16次fixture启动（环境选择器被替换） | 真实解析/注册后的possible/present/online与APIC成员 |
| 真实内核+真实固件+真实环境 | 4次（KVM/KVM+nopv/TCG/TCG max）+QMP热插 | 环境分类对接受与热插的实际影响 |
| 裸机/厂商固件/Xen运行 | 无 | — |

## 5. 合法对照与观察

- 同表异环境（新增、最强）：固件表、镜像、热插槽位相同，只变加速器与`nopv`，把环境分类孤立为唯一差异。
- 同环境异谓词：KUnit before/after只替换谓词（修复还改了topology.c，不是完整历史内核对照）。
- 历史修订链：6修订投影，显示过窄/过宽交替修复。
- 配置对照：LAPIC/x2APIC、legacy/modern表、MADT45误归类。
- 观察：hypervisor识别行、“Allowing N present plus M hotplug”、sysfs集合、QMP回复、内核热插日志（`CPU1 has been hot-added`/`Unable to map lapic`）。

## 6. 判定步骤与边界

1. 固定版本、配置（KVM_GUEST、HYPERVISOR_GUEST、ACPI_HOTPLUG_CPU、NR_CPUS/FORCE）与启动参数（`nopv`）。
2. 取实际固件表头/版本，确定能力语义是否适用（不适用的关系判`not_applicable`）。
3. 登记政策依据与作用域，单独登记“作用域条件由哪个提供者给出”。
4. 在同表异环境下观察提供者输出（识别行）与接受结果，按阶段采样possible。
5. 以实际消费（热插、上线）检验后果，不把QEMU接受热插请求当作内核可用。
6. 交不变公共核心；采样不升格为期限，政策范围观察与规范违反分开。

边界：裸机规范行为只有投影与fixture证据；没有厂商固件、畸形/混合表、online-capable真实表、未开KVM_GUEST的内核；Xen PV/HVM真实运行在本机不可行（QEMU Xen仿真被宿主KVM拒绝）。

## 7. 自动化分工

- 程序：工件SHA、投影执行与逐例计数、fixture注入与KUnit判定、QEMU/QMP驱动、console观测适配、核心四态判定、控制拒判。
- 研究者：规范/政策区分与作用域、环境分类提供者认定、合法环境对照设计、关系与阶段、“政策范围观察≠缺陷”的定性。
- 模型：本家族本阶段0调用。

## 8. 可复用部分与迁移成本

可复用：核心与四态规则；QEMU+QMP真实启动/热插驱动（同样适用于其他“启动时预留、运行时消费”的资源）；console观测适配框架；同表异环境的对照设计。迁移需替换：固件表来源与版本判定、政策依据登记、环境/平台分类提供者清单、消费动作（热插、上线或其他）。

## 本阶段结论

形成两条可复用认识：（1）**规范、兼容政策与实现事实必须分层登记**，兼容政策有作用域；（2）**政策作用域条件本身有提供者，提供者资格须单独检验**——ACPI用“识别到hypervisor类型”提供“是guest”，实测在TCG与`nopv`下覆盖不足。后者与CPU导出的“用途决定来源资格”同属来源资格机制，但对象从数据来源扩展到政策条件来源。观察均未确认、未外报；独立正例/正常仍0/0。
