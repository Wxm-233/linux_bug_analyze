# N2.20 隔离资格判读（模型前）

2026-10-22。只读已冻结的 selection/protocol/material plans、`documents_P01/P02.json` 所绑定的各八份父版全文、`pre_qualification_review.md`、`contact_review_pre.json`、`input_freeze.json` 和唯一已放开的 `repair_evidence.json`。**本意见保存前没有本轮付费模型调用，也未读任何本轮模型回答**；不增补源码、配置、构建或启动。子提交说明是修复者的历史描述，`Fixes:` 是关联线索，不代替本轮运行或接口规范。资格是研究侧有限裁定，不是 N1 自动提取结果。

## P01：限定的旧义务、因果链与范围

父版 `arch/x86/kernel/acpi/boot.c` D01:1728–1738 在 `CONFIG_X86_LOCAL_APIC && !CONFIG_X86_MPPARSE` 下，当 `acpi_disabled || acpi_noirq` 时让 `acpi_mps_check()` 返回 1。D03:955–960 的 `setup_arch` 调用点据此设置 `apic_is_disabled` 并清 APIC capability；D03:1199 把 `topology_apply_cmdline_limits_early()` 排在 D03:1205–1211 的 ACPI/平台 SMP 解析及 possible-map 初始化之前。D02:427–441 在 `apic_is_disabled` 或 `setup_max_cpus=0` 时把 `nr_cpu_ids` 早期降到 1。D02:444–458 的后期 `restrict_to_up()` **已明确对 Xen PV 作例外**：因 PV 不按通常方式宣告本地 APIC，却提供模拟拓扑，不应照普通 APIC 状态限制。D04:149–160 的 `xen_pv_smp_config()` 打算为 `i<nr_cpu_ids` 的 vCPU 登记模拟 APIC 并设置 `smp_found_config`，D04:443–455 对非 initial Xen domain 指向此解析器；D03:1205–1211 的先后意味着若编号界限在 D02:427–441 被提前降到 1，后面的 PV 例外已不能重新取得多槽。公共 D07:1550–1559 先准备再进入 `smp_init()`；D06:1000–1018 按 `setup_max_cpus` 尝试启动非 boot CPU，实际可枚举逻辑域却已缩小。这条链支持“有可用的多个 PV vCPU 时，不应仅因 PV 禁用 ACPI 而把公共逻辑 CPU 上限变为 1”的**先有用途义务**，不是从子补丁的新规则倒推旧 ABI。

上述是条件链，不是本轮完整运行证明：需 Xen PV DomU、`CONFIG_X86_LOCAL_APIC && !CONFIG_X86_MPPARSE`、该 PV 环境的 `acpi_disabled || acpi_noirq`、没有 `nosmp/maxcpus=0/nr_cpus=1/possible_cpus=1` 等显式用户限额，且原本有两个及以上 vCPU。固定父版八文件给出了关键分支与 PV 多 vCPU 路径，但未给目标 `.config`、Xen 选择 hook 的完整调用者、该 DomU 的 ACPI 赋值点、实际 vCPU 数/启动记录。子提交说明明确声称 Xen PV DomU 禁用 ACPI 且可配置多个 vCPU，标注 `Fixes: 7c0edad3643f`；这提供历史回归主张，尚非本轮独立复现。源级反事实为：若上述合法组合成立，父版 D01→D03→D02 的顺序造成过早限 1；具体机器是否经历此组合仍未知。

唯一子版差分只改 x86 ACPI 检查：加入 Xen header，在 D01:1729 所在条件编译分支内，`xen_pv_domain() && !xen_initial_domain()` 时先返回 0，避免该处因 ACPI 状态关掉 APIC。它**没有**普遍修改公共 `smp_init`、CPU ISA 映射或所有 ACPI-off 路径；Dom0、普通 x86、明确 `nosmp`/上限、其他来源的 APIC disabled 不由此豁免。修复说明与差分同父版链吻合，因而 P01 可作为**有限源级缺陷候选资格：eligible**。这不等于真实内核已复现或独立阳性计数。机制主要是 **x86 上 Xen PV guest 模式与 ACPI/MPS 回退假设不匹配**，再经架构早期 `nr_cpu_ids` 传给公共 SMP 消费而暴露“可用多 vCPU 却仅一槽”；LoongArch ISA 本身不是 P01 故障因子。这里的不对称是 Xen PV DomU 与其他平台模式，跨 ISA 材料仅提供方法参照，不能把平台差异偷称 CPU ISA 因果。

## P02：同用途来源，正常保证为何不足

P02 与 P01 同父版，LoongArch D02:41–44 的 `plat_smp_setup()` 调 D01:315–327；D03:611–614 在 `setup_arch` 里随后执行 possible-map 预填。D01:281–308 的 `CONFIG_OF` 路线只取可用 FDT CPU 节点、按硬件 ID 与逻辑 CPU 建双映射并置 possible/present；D04:61–97 的 ACPI/MADT 路线分两遍处理 enabled/disabled，把识别的 CPU 置入 possible，enabled 才置 present；D03:568–588 以 `num_processors+disabled_cpus` 和当时 `nr_cpu_ids` 建最终逻辑域。D01:568–579 的 `smp_prepare_cpus()` 在公共 D07:1550–1559 进入 `smp_init()` 前准备架构状态。由此能定位**同一公共用途**：架构/平台来源给逻辑 possible/present 与上限，随后公共 SMP 使用。不能要求原始物理号等于逻辑号，不能要求 possible 全部 present。

若存在同时合法的 `CONFIG_SMP && CONFIG_OF` 配置、有效且至少两个可用并不重复的 FDT CPU 节点、`nr_cpu_ids>=2`、`setup_max_cpus>=2`、有效 boot ID 与节点顺序，而且未被其他参数/平台约束限 1，则上述 FDT 源级路径**可能**保持至少两个逻辑槽；ACPI/MADT 路线也要求有效固件表、处理成功和相应配置。这些是实质、非“无告警”或关闭功能的条件，但固定包没有 `.config`/Kconfig 可行性见证、有效 FDT 或 MADT 实例、选定分支、真实启动及后续 secondary 成功记录。P02 D01:334 的 `parse_acpi_topology()` 即使在 FDT 路线被调用，所需 PPTT/回退结果也未闭合；仅见 D01:337–339 设置 present/邮件不能推断完整 bringup 正常。尤其 P02 既不是 Xen PV DomU，也没有 P01 的 `acpi_mps_check()`→`apic_is_disabled` 同条件路线，故不能用“另一 ISA 未见该 WARN/该函数”充作同条件正常真值。

因此 P02 只达到**同用途参考源码候选**，没有满足本协议的合法、非空且绑定实际配置/固件的同用途正常保证；`P02_reference_gate=insufficient`。此裁定不是说 LoongArch 路径错误，也不是说上面条件不可实现，而是固定证据无法认证条件实例或完整正常对照。不得为了付费试跑改用未选候选、补第九份全文或把造出的双节点情境当已观测正常。

## 接触、家族与资格总界

P01 属于旧 500 短判定池；历史 ACPI 路径及 `acpi_is_processor_usable` helper 已接触，既有 LAPIC/x2APIC 能力模式原型也接近，但受限记录未核实本次 `acpi_mps_check` 目标位置是否开发中已读，且同修复家族未知；哈希未命中旧索引不证明独立。本次 P01 的 eligible 是**缺陷研究资格**，不升级为正式独立正例。P02 在限定八条历史记录无同路径命中，只能说该范围未见；旧模型预训练、其它记录、同家族及独立正常资格仍未知。两组都没有实机配置与运行真值。P01 平台/guest 模式机制和 P02 另一 ISA 的有限参考不能组成已验证的“CPU ISA 对照”。

门控结论：`P01_defect_gate=eligible`；`P02_reference_gate=insufficient`；依事前协议任一不足即 `ready_for_paid_parent_trial=false`，本轮应零付费调用、保留全部已冻输入与不足，不换例或补材料。完整本文件只供后续研究审阅，先对主任务仅传门控状态。
