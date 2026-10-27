# 已有原型案例的五维台账（初版）

更新时间：2026-09-26。九项原型的修复提交和验证层级来自 [`../CONTRACT_MATRIX.md`](../CONTRACT_MATRIX.md)；本轮又用本地 Linux Git 树追查了部分前置提交、修复说明和配置可达性，结果见下表后的“来源与纳入口径审计”。**原型成立不自动等于已在受支持配置中发生且被持久修复的缺陷。** 架构栏只写现有实验/说明直接支持的条件；纵/横向及错误引入侧需要补做来源核查时写“待核实”。

| 案例（修复提交） | 触发架构/平台和子系统 | 纵/横向；错误引入侧 | 修复合入日 | 已有验证层级与待办 |
|---|---|---|---|---|
| Btrfs [`6f93e834fa7c`](https://github.com/torvalds/linux/commit/6f93e834fa7c5faa0372e46828b4b2a966ac61d7) | 64K 页/扇区条件；Btrfs 挂载选项 | 纵向几何时序候选；公共 Btrfs 侧，首次生效日期未定 | 2021-09-07 | 源码顺序投影，18 组/版本；已追临时 4K 几何到实际 superblock 几何的调用顺序，未做真实挂载 |
| fbnic [`4bd451f4c285`](https://github.com/torvalds/linux/commit/4bd451f4c2851eee7b6e17bb6fd6c9caaadbdc18) | 4K/16K/64K 页；网络设备 DMA 描述符 | 防御性布局改进；受支持配置中的缺陷未证实 | 2025-10-16 | 准备函数级对照，18 组/版本；历史 Kconfig 仅支持 x86_64 正常运行，大页输入是配置外机制对照 |
| parisc [`d97180ad68bd`](https://github.com/torvalds/linux/commit/d97180ad68bdb7ee10f327205a649bc2f558741d) | parisc；调度时钟/clocksource | 条件性架构策略；本次修复后来被撤销 | 2021-09-09 | 初始化函数及调用顺序投影，14 组/版本；2022-05-08 因 32 位内核启动时 RCU stall 被撤销，不能视为持久有效修复 |
| VT-d [`6f5dc7658094`](https://github.com/torvalds/linux/commit/6f5dc7658094610debe2fad1b09a2034e14857b1) | Intel VT-d；IOMMU 映射权限 | 纵向能力契约候选；引入侧 `eea53c581688` | 2025-05-16 | QEMU 内核页表检查，14 组/版本；未测设备 DMA/IOTLB，未找到具体设备故障报告 |
| ARM SMMU [`8c73c32c83ce`](https://github.com/torvalds/linux/commit/8c73c32c83ce7f3c31864cb044abd3daefacd996) | ARM SMMU；IOMMU 域状态转换 | 纵向候选；引入侧待核实 | 2024-02-29 | 真实函数加状态/硬件替身，14 组/版本；未测实际 DMA 与并发 |
| ACPI [`adbf61cc47cb`](https://github.com/torvalds/linux/commit/adbf61cc47cb72b102682e690ad323e1eda652c2) 及历史 | LAPIC/x2APIC 固件记录；CPU 枚举 | 规范/虚拟机环境条件冲突；两项 `Fixes:` 前置链，纵/横向待裁定 | 2025-12-14 | 六种历史源码状态、每模式 8 次内核启动；继续核对版本与平台适用性 |
| NUMA [`e130242dc351`](https://github.com/torvalds/linux/commit/e130242dc351f1cfa2bbeb6766a1486ce936ef88) | native/compat ABI；NUMA 位图转换 | 纵向候选；引入侧待核实 | 2021-09-08 | 帮助函数及部分入口链对照，另有现行内核调用观察；历史完整 syscall 链仍未复现，剩余边界待核对 |
| perf [`aa6a6a2d16c1`](https://github.com/torvalds/linux/commit/aa6a6a2d16c1e2e27e986936369959d70316199f) | s390x 大端；perf 配置 union | 表示契约候选；引入侧 `159ca97cd97c` | 2026-02-24 | 大小端对照、s390x 用户态模拟；属于工具层，须与内核核心样本分层 |
| s390 topology [`a052096bdd68`](https://github.com/torvalds/linux/commit/a052096bdd6809eeab809202726634d1ac975aa1) | s390 CPU 热插拔；拓扑通知 | 纵向时序失配；s390 提供者旧顺序与新调度消费者共同构成 | 2021-09-07 | mask 函数和生命周期投影、两种不完整修复；已追到 `sched_core_cpu_starting()` 2021 年引入，未运行真实通知链 |

补充但不计入以上九项：调度拓扑 [`661f951e371c`](https://github.com/torvalds/linux/commit/661f951e371cc134ea31c84238dbdc9a898b8403)，修复日 2025-09-03。已有 8 组显式上下文函数对照；原始上游告警和真实 NUMA 拓扑尚未复现，见 [`../holdout_review/README.md`](../holdout_review/README.md)。

## 来源与纳入口径审计（本轮）

下表的“前置提交”指已找到的**代码来源或消费条件变化**，并非都能证明它就是首次可运行故障。`Fixes:` 可定位修复者指定的引入提交，但仍需核对适用配置与历史调用链。“引入→主线修复”只作辅助跨度，不能替代老师要求的两个时间段。

| 原型 | 已核对前置来源及时间 | 当前纳入判断与后续证据 |
|---|---|---|
| Btrfs | 旧 `open_ctree()` 先以临时 `fs_info->sectorsize=4096` 调用 `btrfs_parse_options()`，其中 `max_inline` 上限读该字段；解析之后才以 `btrfs_super_sectorsize()` 改为磁盘 superblock 的真实值。临时 4K 赋值可追到 [`da17066c4047`](https://github.com/torvalds/linux/commit/da17066c40472c2d6a1aab7bb0090c3d285531c9)（2016），但该提交主要是字段迁移，之前已有相近的 `root->sectorsize` 逻辑。后续 [`0b246afa62b0`](https://github.com/torvalds/linux/commit/0b246afa62b0cf5b09d078121f543135f28492ad) 仅将访问改写为 `info->sectorsize`，**不是**语义引入提交 | 64K 页/扇区条件下，用户请求上限被临时 4K 值截断；修复将真实几何的赋值移到解析之前。已核对生产者→消费者顺序，仍无历史真实挂载和首次生效日期，不能按 2016 年某行 blame 计算缺陷跨度。 |
| fbnic | `fbnic_bd_prep()` 写描述符但未移动指针的循环可追到 [`0cb4c0a13723`](https://github.com/torvalds/linux/commit/0cb4c0a13723ef6dd06be8f913443897a0ffccb5)（2024-07-15） | 补丁明确说当时“不是一个 fix”，`drivers/net/ethernet/meta/Kconfig` 为 `X86_64 || COMPILE_TEST` 且排除 s390。4K 是正常受支持页大小，16K/64K 属编译/假设配置；**不计已发生的跨架构缺陷**，保留边界检测机制的负对照。 |
| parisc | 2021-09-09 提议按 cr16 同步状态决定 `sched_clock` 稳定性；后续 [`7962c0896429`](https://github.com/torvalds/linux/commit/7962c0896429af2a0e00ec6bc15d992536453b2d) 于 2022-05-08 明确撤销，理由是 32 位内核启动发生 RCU stall | 原型验证了当次补丁改变的分支条件，**没有**证明它是正确的持久修复；暂从“已确认修复案例”统计中剔除。研究价值在于架构契约有位宽/时钟条件，需重新界定正确目标。 |
| VT-d | 修复说明明确指向 [`eea53c581688`](https://github.com/torvalds/linux/commit/eea53c5816889ee8b64544fa2e9311a81184ff9c)（2021-04-07）对第二级页表写权限的统一禁用；到修复合入 2025-05-16 为 1500 天 | 页表原型支持“硬件可用能力被通用化抹掉”的行为差异；提交未给可核实的真实设备故障报告，暂作为**能力契约候选**，不把 1500 天说成实际故障暴露时间。 |
| ARM SMMU | 修复说明指出新的 STE 自动过渡允许移除旧的双重写入；本轮未定位唯一的首次故障提交 | 旧/新和部分修复原型支持中间状态的风险，但真实 DMA/并发未运行；引入日、发现日均待查。 |
| ACPI | 修复有两个 `Fixes:`：[`fed8d8773b8e`](https://github.com/torvalds/linux/commit/fed8d8773b8ea68ad99d9eee8c8343bef9da2c2c)（2023-03-30）与 [`f0551af02130`](https://github.com/torvalds/linux/commit/f0551af021308a2a1163dc63d1f1bba3594208bd)（2024-03-06）；到 2025-12-14 修复分别为 990/648 天 | 这是固件规范与 QEMU 兼容条件相互影响的历史链，不能压成单一引入事件。提交有 `Closes:` 报告链接，但本轮无法核实原报告正文/日期，发现日留空。 |
| NUMA | 2021 修复说明概括多个 native/compat 位图问题，并非单个 `Fixes:`；现有 32 位和 compat 入口实验仍有边界待核对 | 暂不指定唯一引入日；先分问题子链，避免把整个综合补丁计一个可定时的引入事件。 |
| perf | [`159ca97cd97c`](https://github.com/torvalds/linux/commit/159ca97cd97ce8cc65364fee37319823b5ffb5bd)（2026-01-14）是明确 `Fixes:`；到 2026-02-24 主线修复为 41 天 | 大端 s390x 实验与提交给出可观察反例。属于 perf 用户态工具，须与内核缺陷**分层**统计；无独立发现日期。 |
| s390 topology | 旧 s390 `smp_start_secondary()` 的 `notify_cpu_starting(cpu)` 在 `set_cpu_online()` 和 `update_cpu_masks()` **之前**，这一顺序可追到 [`52aeda7accb6`](https://github.com/torvalds/linux/commit/52aeda7accb6d2e511a1b89142cbbf6fd2c12565)（2020-03-23）。共享调度代码的 [`9edeaea1bc45`](https://github.com/torvalds/linux/commit/9edeaea1bc452372718837ed2ba775811baf1ba1)（2021-05-12）新增 `sched_core_cpu_starting()`；`CPUHP_AP_SCHED_STARTING` 经 `sched_cpu_starting()` 在 notifier 阶段读 `cpu_smt_mask(cpu)` 并设置 `rq->core`。`CONFIG_SCHED_CORE` 依赖 `SCHED_SMT`，s390 提供后者 | 这是“旧架构提供时序 + 新共享消费者”的组合链；2021-05-12→2021-09-07 为 **118 天代码跨度**，不等于首次发现用时。修复还引入 `cpu_setup_mask` 使尚未 online 的 CPU 参与 mask 准备，不能只移动调用顺序。真实内核通知链尚未运行。 |

### “准备早于消费”机制的适用条件

本轮把同一问题形式分别落到三种状态，避免只凭“热插拔”“初始化”等词合并：Btrfs 的状态是磁盘 superblock 扇区大小，s390 的状态是拓扑/SMT CPU mask，另见 [`prototype_results.md`](prototype_results.md) 中 arch_topology 的 cacheinfo 和 ARM64 Hyper-V 的 per-CPU 输入页。可人工写成条件契约：**在配置条件 A 成立且消费者 C 可执行时，提供者 P 必须先成功准备其读取的状态；如果 P 失败或资源在下线流程失效，C 不得按已就绪处理。**

| 案例 | 条件 A | 提供者 P → 消费者 C | 旧状态与修复 |
|---|---|---|---|
| Btrfs | 磁盘 sectorsize 大于临时 4K，用户指定 `max_inline` | 读取 superblock 几何并写 `fs_info->sectorsize` → `btrfs_parse_options()` 检查上限 | 旧版先解析后赋真实值，修复提前赋值；普通 4K 配置是不能误报的对照 |
| s390 | CPU 热插拔、SMT 且编入 `SCHED_CORE` | `update_cpu_masks()` 建立包含启动 CPU 的拓扑 mask → `notify_cpu_starting()` 到 `sched_core_cpu_starting()` | 旧版先通知后更新；修复同时提前更新并以 `cpu_setup_mask` 表示尚未 online 的 CPU；只改一处不足 |
| arch_topology | CPU 重新上线且 cacheinfo 已被下线流程释放 | `detect_cache_attributes()` → `last_level_cache_is_shared()` 计算 LLC 掩码 | 旧版靠启动期检测、上线时消费先于恢复；修复在消费前重新检测 |
| ARM64 Hyper-V | 有可能在 IRQ affinity 热插拔回调中进入 vPCI 消费路径 | `hv_common_cpu_init()` 分配每 CPU 输入页 → vPCI 中断重定向读取 | 旧动态注册点晚于 IRQ affinity 状态；修复提前，且下线时保留资源供晚些的重定向使用 |

这些关系目前由人工沿历史源码识别，再由各特化原型核对；**尚未自动抽取 P/C/A，也没有对未知提交做盲测**。系统层检查可以从 CPUHP 状态表、调用图、资源读写和配置约束提取候选顺序边，再用实际反例与正常配置排除误报。若只检查“函数结束时状态已准备好”，会漏掉 arch_topology 中读取后才检测的人工半修复；若不带条件 A，则会误报 Btrfs 的普通 4K 配置。

本次又用事前固定的独立 RISC-V 提交 [`c1d610586946`](https://github.com/torvalds/linux/commit/c1d6105869464635d8a2bcf87a43c05f4c0cfca4) 检查这一机制是否仅适合热插拔。其状态是 **`GFP_KERNEL` 分配可用性**，提供者是 `mm_init()` 中的 `kmem_cache_init()` 加后续 GFP mask 放开，消费者是拓扑解析在 DT 有 `capacity-dmips-mhz` 时的 `kcalloc()`；旧 RISC-V 启动入口早于提供者，修复后晚于提供者。ARM64 同期使用较晚入口。输入条件是当时无效的 RISC-V DT 属性，故把它列为**有条件的机制迁移对照**，不混入九项旧原型或新的 12 条源码确认缺陷。修复说明的 `Fixes: 03f11f03dbfe` 合入 2019-07-22，到 2023-01-25 修复为 1283 天**代码跨度**；首次真实故障与发现日均未知。预冻结方案、标注、脚本和结果见 [`temporal_holdout_plan.md`](temporal_holdout_plan.md)。

九项历史原型的“引入→发现”和“发现→修复”仍均缺**可独立核实**的发现日期，两个目标时间字段为未知（0/9 可计算）。本轮尝试读取 ACPI 的 `Closes:` 邮件和 NUMA 的报告链接，但链接正文不可达；邮件 ID 或修复提交的 author date 不能自动代替首次发现日。原研究材料所称的 13 条源码案例仍需找回逐条清单、排重并与九项原型及调度案例对齐。
