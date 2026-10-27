# 两候选的事后资格与机制裁定

2026-10-17。此评审只依据本阶段的 `protocol_pre.json`、`parent_files.json`、登记的 A/B 父版文件、`repair_material.json`、`parent_scope_review.md` 和 `exposure_supplement.json`。父版文件由 `parent_files.json` 绑定到各自的父提交与 SHA-256。未读本轮模型 final/partial、组件结果或后续结论，未补读包外源码、规范、配置或运行结果。以下是**读修复材料之后的研究侧资格裁定**，不能记为模型自动提取、组件独立检出或运行证明。提交作者的说明是问题线索，不单独充当规范或实际效果证据。

## A：0c2f6d0，Intel CPUID 可见范围

**父版中的可支持机制。** `arch/x86/kernel/cpu/common.c:896–918` 将 CPUID 叶 0 的最大叶号写入 `c->cpuid_level`；`:972–1006` 用它决定是否读取叶 6、7、0xd 等能力。启动 CPU 路径 `:1588–1600` 在厂商识别后，先取能力、初始化拓扑，才进入厂商 `c_early_init`；另一识别路径 `:1737–1756,1805–1832` 也在厂商 `c_init` 前取能力和解析拓扑。`intel.c:272–283,601–605,948–955` 显示 Intel 钩子原本在家族/型号门控后才尝试清除限制 CPUID 的 MSR 位；仅 `msr_clear_bit(...) > 0` 时重读最大叶号并再取能力。因此，在该硬件位确实限制可见叶、清除成功且 CPUID 可见范围随之扩大等前提下，父版存在“条件性准备晚于同一 x86 通用读取”的源码顺序风险。后一次 `get_cpu_cap` 也不能自动证明先前的拓扑派生值被重算。

**父版→修复。** 已保存的子提交 hunk 在 `early_identify_cpu` 与 `generic_identify` 中把 `intel_unlock_cpuid_leafs(c)` 放到 `get_cpu_cap(c)` 之前；新增函数有 Intel 厂商和家族/型号门控，尝试清除限制位并更新 `cpuid_level`，同时从 `early_init_intel` 移除原有的较晚清除/重读逻辑。这个变更与上述条件性顺序机制一致；它不要求厂商/型号识别本身在任何 CPUID 使用之前完成解锁。`repair_material.json` 的 A `diff_paths` 另列 `arch/x86/include/asm/cpuid.h`，但保存的 diff 没有其 hunk；不能凭该路径列表扩大可见修复断言。

**资格。** `common.c` 是 **x86 单 ISA 内**的通用 CPU 识别，`Makefile:20–22,36–39` 将 Intel 实现置于 `CONFIG_CPU_SUP_INTEL` 条件下。这里可见的是 Intel 厂商/CPU 型号与同一 x86 识别流程的差异，不是两个 CPU ISA 共用 Linux 公共消费者的暴露配对。因此 A **不纳入核心跨 CPU 架构正例**；也无已证明的同用途正常对照。包内没有 `cpu_init_topology`、`cpu_parse_topology` 的实现、MSR 助手行为、有效配置及实际受限/非受限机器运行；不能认定具体拓扑错误、修复有效性或跨架构影响已被证明。保留为“厂商条件下首次消费前准备”的局部研究候选，不给阳性/正常标签。

## B：a8c73b8，Intel IOMMU PMU 与 perf/CPUHP

**父版中的可支持机制。** `drivers/iommu/intel/Kconfig:12–14,89–98` 的 Intel IOMMU 性能事件依赖 `X86`、`INTEL_IOMMU`、`PERF_EVENTS`；`Makefile:11` 按配置纳入 `perfmon.o`。`perfmon.c:588–610` 检查设备能力，`:612–709` 构造 PMU 并挂到 IOMMU；`:551–570` 向公共 perf 注册回调。`:776–818` 的驱动 CPUHP 回调分别管理全局 `iommu_pmu_cpu_mask`、各实例 `iommu_pmu->cpu` 和 context 迁移，两个状态不能视作同一对象。`:824–846,859–875` 中先注册 perf PMU，再建立多实例 hotplug 状态并添加实例；登记父版的 `include/linux/cpuhotplug.h:341–384` 明确建立多实例状态本身**不调用**回调，添加实例才对已到状态的在线 CPU 调用启动回调。这证明一个接口时序边界，而非现有代码已经违反边界。所见 `perfmon.c:298–317` 的 event 初始化仅检查事件类型、采样期和 `event->cpu >= 0` 等，不能据此指定各实例 `cpu` 的首次消费。

**父版→修复。** 已保存的子提交 hunk 将 `pmu.scope` 设为 `PERF_PMU_SCOPE_SYS_WIDE`，移除驱动的 cpumask 展示、CPUHP 回调/实例登记、迁移清理及 `iommu_pmu` 中的 `cpuhp_node/cpu` 字段。作者说明称 generic perf 已支持 system-wide PMU；这是变更动机，包内没有公共 perf 的 scope 消费实现或版本化接口契约，不能由说明推断等价迁移、正确性或适用的运行配置。`repair_material.json` 的 `diff_paths` 还列出 `include/linux/cpuhotplug.h`，但保存的 B diff 没有其 hunk；本评审只对可见 hunk 作断言。

**资格。** B 是受 x86/Intel 设备配置限制的提供者连接到 Linux 公共 perf/CPUHP API；“用了公共 API”不足以成为 CPU 架构间的同用途共享消费者。旧版可能是可用设计，新版也可能是通用框架能力更新后的简化；**cleanup 不证明旧版有缺陷，也不证明新版是同用途正常对照**。缺公共 perf 注册/调度/迁移实现、CPUHP 执行体、真实配置和合法事件路径的成功观测，无法判定首次消费前是否需要/已有哪个状态、是否发生语义失配或正常满足。B **既不纳入核心跨 CPU 架构正例，也不纳入同用途正常对照**，保留为接口迁移待核材料。

## 家族、分母与证据边界

两候选来自旧 500 的筛选任务；`exposure_supplement.json` 仅证实有限任务索引命中和结果/响应文件存在，未读其中判断。有限开发记录中未找到 A/B 的既有源码复核，不等于全局未接触。已读的 `5ebf512f` 排除；与 B 同作者且标题相近的 `9e9af8bb` 暂缓，作者、日期、标题及路径既不能确认同一修复家族，也不能证明独立家族；本轮不补替换样本。A 与 B 属不同可见子系统/机制，但不以这些元数据证明完整家族关系。

按照 `protocol_pre.json` 的核心正例要求（架构依赖的差异、同用途共享消费者、有依据的破坏条件及环境间暴露原因）和正常对照要求（同用途、合法路径、已支持的满足行为），本次**新增合格正例 0、合格正常对照 0**。A 的条件性代码顺序可指导以后查“厂商准备与通用读取的先后”，B 可提示查“驱动自管状态与框架 scope 的责任边界”；两者目前都不能扩大跨架构泛化分母。若要复核，应另行预登记并取得对应的共同消费者/适用配置/实现及合法路径证据，不能将这次读修复后的建议回填成自动发现。
