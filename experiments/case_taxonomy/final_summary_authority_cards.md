# 最终总结前的接口权威证据卡（2026-09-28）

本文件服务于 [W4 代办](../../../当前代办.md)：当两个架构或两条代码路径对同一接口的理解不同，先固定**接口版本、可达配置、调用路径和消费者**，再找适用于这一组合的 ABI、格式、规范或本版实现声明。源码中的默认值、补丁标题和多数架构的写法都不能单独决定权威。以下两卡区分“可裁定的历史实现门控”与“观察到分歧但尚待接口裁定的 ABI 边界”；不把候选检查写成已确认的新缺陷。

## 卡 T：历史 CPU topology sysfs 的原生提供者与 fallback

| 字段 | 可回溯证据与判断 |
|---|---|
| 接口、版本 | `die_id`、`die_cpus`、`die_cpus_list` 三个 sysfs 属性；比较 Linux [`2c4dcd7fd57b^` 与 `2c4dcd7fd57b`](https://github.com/torvalds/linux/commit/2c4dcd7fd57b20a21b65da04d89c38a7217d79cf)。只裁定这一历史 die 属性家族的静态导出条件，不把规则外推到任意 CPU 拓扑接口。 |
| 配置、路径 | 历史 `CONFIG_SYSFS=y` 且对应 topology 驱动可构建；架构和 `CONFIG_SMP` 均是条件。从 [`arch/x86/include/asm/topology.h:108–121`](https://github.com/torvalds/linux/blob/2c4dcd7fd57b20a21b65da04d89c38a7217d79cf/arch/x86/include/asm/topology.h#L108-L121) 读取原生 ID 和在 SMP 下定义的原生 cpumask；其他架构须逐一核查。再经过 [`include/linux/topology.h:183–210`](https://github.com/torvalds/linux/blob/2c4dcd7fd57b20a21b65da04d89c38a7217d79cf/include/linux/topology.h#L183-L210) 的原生宏判断与 fallback，最后到 [`drivers/base/topology.c`](https://github.com/torvalds/linux/blob/2c4dcd7fd57b20a21b65da04d89c38a7217d79cf/drivers/base/topology.c) 的 show/read、属性数组注册。 |
| 消费者 C | 用户态读取 `/sys/devices/system/cpu/cpuX/topology/` 下三个属性；同版[稳定 ABI 描述](https://github.com/torvalds/linux/blob/2c4dcd7fd57b20a21b65da04d89c38a7217d79cf/Documentation/ABI/stable/sysfs-devices-system-cpu#L27-L37)把 `die_id` 描述为依架构/平台而定的 die ID，`die_cpus` 为同 die CPU 集合。存在这个文档条目并不意味着每个架构都必须创建文件。 |
| 权威来源 P 与状态 | 同版[管理文档](https://github.com/torvalds/linux/blob/2c4dcd7fd57b20a21b65da04d89c38a7217d79cf/Documentation/admin-guide/cputopology.rst#L5-L52)明示 die 文件只在架构提供相关宏时创建；修复版在 fallback 定义**之前**同时要求 `topology_die_id` 和 `topology_die_cpumask`，并用 `TOPOLOGY_DIE_SYSFS` 门控三个导出位置。fallback 的 `-1`、`cpumask_of(cpu)` 是接口缺省表示，不等于真实 die 能力。对这一版的**导出门控规则**有源码和文档依据；这不证明每台机器的硬件拓扑 ID 一定正确。 |
| 旧版、修复版、正常对照 | 旧版属性无此守卫；先前的[条件矩阵](prototype_results.md)显示所查 s390+SMP、ARM64+SMP 旧版仍导出三项，修复后不导出。所查 x86+SMP 具两项原生宏，修复后仍导出；x86 非 SMP 没有原生 cpumask，修复后不导出。此为历史源码/预处理条件实验，未启动旧内核核对真实 sysfs 文件。 |
| 可添加的检查 | 对**此版本此家族**检查 `export(die_*) ⇒ native(topology_die_id) ∧ native(topology_die_cpumask)`。必须在通用 fallback 前判定 `native`，还须证明属性注册链可达；任一前提无法解析输出 `insufficient`。近邻 [`e795707703b3`](https://github.com/torvalds/linux/commit/e795707703b32fecdd7467afcc33ff1e92416c05) 的 cluster 家族采用相似门控，但仍要单独核对版本和宏名；PPIN 只有运行时单值，不适用双提供者规则。 |

**裁定范围。** 这里能裁定的是 *2021 年该实现何时应该对外导出这三个属性*，不是跨时代的拓扑真值标准，也不以“x86 的行为”为所有架构的规范。旧版 book/drawer 还曾采用不同的 Kconfig 守卫；不能把 die 的历史宏形状强加给 2010 年修订。现有来源提取器的支持范围与拒判见 [topology v3 开发记录](topology_v3_development.md)。

## 卡 N：i386 compat NUMA 位图的声明范围与实际读取

| 字段 | 可回溯证据与判断 |
|---|---|
| 接口、版本 | 32 位 i386 进程调用 `set_mempolicy(MPOL_BIND, nodemask, maxnode=1026)`；运行 `uname -r` 为 `6.18.33.2-microsoft-standard-WSL2`，`/proc/version` 构建时间为 2026-06-18。微软发布了同名 [`linux-msft-wsl-6.18.33.2` 标签，提交 `c21a03b`](https://github.com/microsoft/WSL2-Linux-Kernel/releases/tag/linux-msft-wsl-6.18.33.2)。 |
| 配置、路径 | 运行 `/proc/config.gz` 和同名发布标签的[配置](https://github.com/microsoft/WSL2-Linux-Kernel/blob/linux-msft-wsl-6.18.33.2/arch/x86/configs/config-wsl)在所需项上一致：`CONFIG_NUMA=y`、`CONFIG_NODES_SHIFT=10`、`CONFIG_IA32_EMULATION=y`。发布标签 [`include/linux/nodemask_types.h:7–13`](https://github.com/microsoft/WSL2-Linux-Kernel/blob/linux-msft-wsl-6.18.33.2/include/linux/nodemask_types.h#L7-L13)据此得 `MAX_NUMNODES=1024`。路径为 [`set_mempolicy → kernel_set_mempolicy → get_nodes → get_bitmap`](https://github.com/microsoft/WSL2-Linux-Kernel/blob/linux-msft-wsl-6.18.33.2/mm/mempolicy.c#L1562-L1622)；compat 分支最终调用 [`compat_get_bitmap`](https://github.com/microsoft/WSL2-Linux-Kernel/blob/linux-msft-wsl-6.18.33.2/kernel/compat.c#L193-L220)。 |
| 消费者 C、外部权威候选 P | [Linux `set_mempolicy(2)` 手册](https://man7.org/linux/man-pages/man2/set_mempolicy.2.html)把 `nodemask` 说明为最多 `maxnode` 位，长度按调用者的 `unsigned long` 取整，内核只使用该范围的位；若指定内存范围不可访问则为 `EFAULT`。对 i386 调用者，1026 位取整到 33 个 32 位字，即 **132 字节**。手册是公开 ABI 文字的强证据，但其与内核 `--maxnode` 的历史细节及维护者解释仍需核实。 |
| 发布标签源码中的读取范围 | [`get_nodes`:1592–1618](https://github.com/microsoft/WSL2-Linux-Kernel/blob/linux-msft-wsl-6.18.33.2/mm/mempolicy.c#L1588-L1622)先将 1026 减为 1025，因超过 1024 而进入循环，取 `bits=64`，以 64 位内核字宽计算 `nmask[(1025-1)/64]`，起点为字节 128；[`compat_get_bitmap`:193–213](https://github.com/microsoft/WSL2-Linux-Kernel/blob/linux-msft-wsl-6.18.33.2/kernel/compat.c#L193-L213)对 64 位片段连续读取两个 32 位字，终点为字节 135。于是**发布标签源码**预期检查第 34 个 32 位字；该字位于按 i386 `maxnode=1026` 取整的 132 字节之外。此计算与本地独立 Linux HEAD 的相似函数形状不能混为同一源码版本。 |
| 运行观察 | [原始探针结果](../../analysis_out/numa-padding-20260928/results.jsonl)中，132 字节放在可读页末返回 `-EFAULT`；给 136 字节、额外字为 0 返回 0；仍为 136 字节、只将额外字设为 1 返回 `-EINVAL`。`maxnode=1057`、该字为 1 的正常拒绝对照也返回 `-EINVAL`。实验仅为当前 WSL 的 i386 compat、允许节点 0、该容量边界；没有证明其他架构、真实多节点或历史整内核行为。完整方法见 [NUMA 复核](numa_boundary_2026_09_28.md)。 |
| 历史实验勘误与裁定状态 | 旧 4/32 不一致中 **2 项是 harness 按 `bits` 而非入口 `maxnode` 分配长度的错误**；剩余 **2 项是边界分歧**，补齐字节后得到成功/`EINVAL` 的对照。当前真实调用与发布标签源码给出一致的范围现象，但仅靠同名发布标签、`uname` 和三个配置位，仍**不能证明运行二进制与公开标签逐字同源**；尚未获得维护者对 ABI 边界的裁定，也没有把它确认为新缺陷。 |
| 可添加的检查 | 只在已知用户 ABI 字宽、入口 `maxnode`、内核字宽、`MAX_NUMNODES` 和每段 `copy_from_user`/`compat_get_bitmap` 长度时，计算**实际读取的最大字节偏移**与**调用者按接口声明所需的最后字节**。若后者较小，输出含公式、源码位置、页末/零字/非零字对照的 `review_candidate`；ABI 含义或可达性不明时输出 `insufficient`。不能从一次 `EFAULT` 单独推出应改哪一行，更不能宣称通用检测已实现。 |

**来源边界。** 过去使用的本地 Linux Git `df2908090cda` 是上游 7.3-rc2，**不是正在运行的 WSL 内核源码**。本轮通过官方同名发布标签只读核对了 `mm/mempolicy.c`、`kernel/compat.c`、`nodemask_types.h` 和配置中的相关行；两者逻辑相合，但未取得运行映像与 `c21a03b` 的构建 ID/文件哈希等一一对应证据。因此卡 N 的结论是“公开 ABI 文字、对应版本标签源码与实测之间的待裁定分歧”，不是已完成的内核缺陷判定。

## 分支和防过度推广的对照

- **ACPI**：旧卡锚点 [`aa06e20f1be6`](https://github.com/torvalds/linux/commit/aa06e20f1be628186f0c2dcec09ea0009eb69778) 的 LAPIC 入口覆盖、后续 [`e2869bd7af60`](https://github.com/torvalds/linux/commit/e2869bd7af608c343988429ceb1c2fe99644a01f) 的 x2APIC 覆盖、[`a74fabfbd1b7`](https://github.com/torvalds/linux/commit/a74fabfbd1b7013045afc8cc541e6cab3360ccb5) 的 ACPI 版本来源、[`fed8d8773b8e`](https://github.com/torvalds/linux/commit/fed8d8773b8ea68ad99d9eee8c8343bef9da2c2c) 的旧规范兼容以及最终 [`adbf61cc47cb`](https://github.com/torvalds/linux/commit/adbf61cc47cb72b102682e690ad323e1eda652c2) 的 guest/裸机边界，不能仅因复用一个判定函数合成一条独立缺陷。应分别记录固件条目类型、规范版本、运行环境和 CPU 枚举消费者；见 [旧 13 卡因果审计](legacy_13_causal_audit.md)。本卡不代替 ACPI 规范逐版核查。
- **负对照**：[`parisc d97180ad68bd`](https://github.com/torvalds/linux/commit/d97180ad68bdb7ee10f327205a649bc2f558741d) 后来被 [`7962c0896429`](https://github.com/torvalds/linux/commit/7962c0896429af2a0e00ec6bc15d992536453b2d) 撤销；它提醒我们“修复补丁”并不自动是正确权威。[`fbnic 4bd451f4c285`](https://github.com/torvalds/linux/commit/4bd451f4c2851eee7b6e17bb6fd6c9caaadbdc18) 的大页假设在当时 Kconfig 支持范围外，原型只能展示条件性风险，不能计真实跨架构故障。Tegra BPMP 的[大端支持范围对照](endian_producer_holdout_review.md)也说明局部转换代码不等于平台承诺支持大端运行。

**供最终 Word 使用的表述边界：** topology 的版本化导出检查有文档和历史源码的条件性依据，NUMA 的 ABI 边界有发布标签源码与真实 i386 返回值对照但接口裁定未完。两者共同支持“为自动检查附上权威来源、版本、配置、路径、消费者和拒判状态”的方法；不支持宣布已形成跨任意架构/子系统的通用自动检测器。
