# 跨架构接口契约的证据矩阵与检查入口（初版）

日期：2026-09-26。本矩阵以固定 12 条中的**六条源码确认案例**，加上已有较明确提供者—消费者链的 Btrfs、s390 拓扑两项旧原型，共八条为主。这里的“确认”是源码因果链成立，不等于在历史内核、真实设备上完成复现；两项旧原型也不并入 12 条的 **6/5/1** 分母。八条是目的性选例，不能用其频数估计 Linux 总体分布。逐条来源见 [`case_reviews.md`](case_reviews.md)、[`historical_inventory.md`](historical_inventory.md) 和 [`prototype_results.md`](prototype_results.md)。

**读表口径。** A 是必须同时满足的架构、配置和运行路径；P 是状态或表示的权威来源；C 是已找到的首次相关使用点或对外暴露边界。“旧→新”只写历史源码与现有原型支持的行为，不把函数替身、条件矩阵、顺序投影写成真实故障复现。若 P 是范围上限或能力声明，而非执行中的赋值，检查的是 `C` 的输入是否满足 P 的约束，并非机械要求“P 先执行”。

## 1. 状态在首次消费时必须就绪

| 案例与适用条件 A | 权威来源 P → 首次消费者 C；检查位置 | 旧→新；正常或不适用对照 | 证据层级和未解决项 |
|---|---|---|---|
| **Btrfs `6f93e834fa7c`**：64K 页与 64K 磁盘扇区，`max_inline` 请求超过临时 4K 上限。 | 磁盘 superblock 的 `sectorsize` 应先写入 `fs_info` → `btrfs_parse_options()` 用它裁剪 `max_inline`；检查 `open_ctree()` 中赋值与解析的顺序。 | 旧版先用临时 4K 解析，较大请求被截断，再写真实几何；修复把真实值写入解析之前。4K 几何下旧新应相同；请求不触发上限时不报警。 | 历史源码顺序及每版本 18 组投影；**未真实挂载**，无法指定首次可运行故障日期。[来源](historical_inventory.md) |
| **s390 拓扑 `a052096bdd68`**：s390 次级 CPU 启动/热插拔，`CONFIG_SCHED_CORE` 启用（依赖 `SCHED_SMT`），且 `sched_core_cpu_starting()` 可达。 | `update_cpu_masks()` 及 `cpu_setup_mask` 表示尚未 online 的 CPU → `notify_cpu_starting()` 经调度回调到 `sched_core_cpu_starting()` 读取 `cpu_smt_mask`；检查通知入口。 | 旧版先通知再更新，消费者可见旧 mask；完整修复提前准备并纳入未 online CPU。仅调整先后或仅改 mask 的不完整方案都不足；无此消费链的配置为非适用。 | 历史调用链、mask 函数与生命周期投影，含两种人工半修复；**未执行真实 notifier/并发热插拔**。[来源](historical_inventory.md) |
| **arch_topology `3fcbf1c77d08`**：CPU 下线释放 cacheinfo，重新上线，且与其他 CPU 共享 LLC。 | 当前热插拔周期的 `detect_cache_attributes()` → `update_siblings_masks()` 中的 `last_level_cache_is_shared()`；检查 LLC mask 计算之前。 | 历史函数原型中旧版 CPU1 LLC mask 为 `2`、修复为 `3`；人工“读后才检测”仍为 `2`。原已就绪且共享时均为 `3`，LLC 不同或检测失败时均为 `2`。 | 真实历史函数体的 12 组替身执行；**未运行历史 ARM64 热插拔**，失败路径仍需具体配置核实。[来源](prototype_results.md) |
| **ARM64 Hyper-V `52ae076c3a9b`**：IRQ affinity 回调确实进入 vPCI 中断重定向，且输入页分配成功。 | `hv_common_cpu_init()` 分配 per-CPU 输入页 → vPCI 路径读取/清零；检查 CPUHP 注册状态相对 `IRQ_AFFINITY_ONLINE` 的位置，以及下线后页面存活。 | 旧 `CPUHP_AP_ONLINE_DYN` 在相关 IRQ 状态之后；修复 `CPUHP_AP_HYPERV_ONLINE` 在其之前。若 vPCI 路径不进入，则此消费关系不适用；下线时还需保留页面供晚期重定向。 | 同版本 CPUHP 状态表与调用链的**源码顺序投影**；未执行 Hyper-V、CPUHP 核心或真实重定向。[来源](prototype_results.md) |

这四项共享的只是**带条件的状态契约** `A ∧ reachable(C) ⇒ P 在 C 首次读取前有效`，并在下线时检查资源存活。状态身份、调用边和失败分支必须逐项确定；不能因提交标题含 `hotplug`、`topology` 或某语句被搬移就认定违例。尤其 arch_topology 的人工半修复说明，仅在函数结束检查最终状态会漏掉消费时刻的错误。

## 2. 数据和命令必须落在目标表示范围

| 案例与适用条件 A | 权威来源 P → 使用边界 C；检查位置 | 旧→新；正常或反例 | 证据层级和未解决项 |
|---|---|---|---|
| **shmem `9fd154ba926b`**：可选 PMD 大页；ARM64 64K 普通配置下 `HPAGE_PMD_ORDER=13`，xarray 页缓存上限为 `11`。 | `PAGE_SHIFT`、`HPAGE_PMD_ORDER` 与 `MAX_PAGECACHE_ORDER` 给出可表示范围 → `shmem_is_huge()` 的选择供后续页缓存拆分；在选择 PMD 页之前检查 `order ≤ bound`。 | 旧版在 64K 的三种启用策略仍选不可表示的 PMD 页，修复版拒绝。普通 4K 的 `9 ≤ 9` 时三种策略旧新都保留；禁用策略均不选。 | 提取历史函数编译执行 20 次，9 次旧新选择不同；**未执行 `xas_split_alloc()` 或内核告警**。`BASE_SMALL` 输入是额外假设配置，不作部署事实。[来源](prototype_results.md) |
| **virtio input `95c7b0ad6c69`**：输入 SG 经 DMA 映射、平台实际非缓存一致，且设备写事件数组与 CPU 写字段可能同缓存行。 | 目标架构的 `ARCH_DMA_MINALIGN`、`struct virtio_input` 位置和 `DMA_FROM_DEVICE` 路径 → 设备写 `evts` 与 CPU 写 `lock/ready`；检查 DMA 数组两端是否与 CPU 字段共用对齐单元。 | 旧布局两端共用，完整修复两端隔离。历史 64 项数组恰好 512B，**仅加起始边界**也能过；人工改为 63 项后末端又共用，提示必须重测两端。 | 16 组编译结构布局及源码可达链；**未观察真实 DMA 损坏**。`VIRTIO_F_ACCESS_PLATFORM` 只支持映射路径的条件，不能单独当作非一致性证据。[来源](prototype_results.md) |
| **ARM SMMU `eb6c97647be2`**：range 功能启用，SVA 或 io-pgtable 提出非叶失效，范围为 1/33/65 页等边界。 | 调用者提供 `range` 与 `leaf=false` 语义 → `__arm_smmu_tlb_inv_range()` 编码 TTL/Num/Scale；检查命令合法、非叶 TTL=0 且覆盖请求。 | 旧版在三种页粒度各 1/33/65 页共 9 组生成全零非法字段，修复版 0；只修 1 页仍漏 33/65，只改 TTL 则破坏非叶语义。2/31/32/64 页、叶路径及 range 关闭为必要对照。 | 历史函数与命令队列替身 336 组；上游调用边只做源码追踪，**未执行 SMMU 硬件**。更宽松一页的约定来自修复说明，需与设备模式核对。[来源](prototype_results.md) |

三项的表示对象不同：页阶上限、DMA/cacheline 共享单元和设备命令字段。可共享“在边界处检查可表示性”的方法，**不能**共享一条没有对象、单位和模式条件的正则。

## 3. 公共接口导出必须以架构真实能力为条件

| 案例与适用条件 A | 权威来源 P → 对外边界 C；检查位置 | 旧→新；正常对照 | 证据层级和未解决项 |
|---|---|---|---|
| **die sysfs `2c4dcd7fd57b`**：该历史通用 topology 属性，需同时考虑架构和 `CONFIG_SMP`。 | 此实现以架构头中**原生** `topology_die_id`、`topology_die_cpumask` 声明作导出门控 → `drivers/base/topology.c` 导出 `die_id`、`die_cpus`、`die_cpus_list`；在通用 fallback 宏定义**之前**判断。 | 旧版四组源码配置均导出 3 项，s390+SMP、ARM64+SMP 可能暴露无效默认值；修复后两者为 0，x86+SMP 仍为 3，x86 无 SMP 为 0。 | 六处属性入口及四组预处理条件矩阵；**未启动这些历史内核检查 sysfs**。“x86 需求→公共导出→其他架构”有横向源码链，仍保留横向候选口径。[来源](prototype_results.md) |

同一时期的 s390 perf 白名单改动 `a6e62743621e` 必须与 die 文件提供者分开：它只在文件实际存在时改变用户态谓词；所查主线 s390 配置并不导出该文件，故它是条件性兼容对照，**不是第九条已确认案例**。

## 从矩阵到自动检查：先做有明确边界的两项

| 优先级与候选检查 | 要读取的证据及确定性条件 | 必须有的正常/反例；当前状态 |
|---|---|---|
| **1. 能力导出** | **对此历史 die 接口**，解析各架构与 `CONFIG_SMP` 的预处理条件，先区分原生能力宏与通用 fallback，再检查 `export(die_*) ⇒ native(topology_die_id) ∧ native(topology_die_cpumask)`。建议在属性注册/可见性处报告具体架构、宏来源和导出路径。 | x86+SMP 应继续导出；s390+SMP、ARM64+SMP 和 x86 无 SMP 不能用 fallback 伪装支持。现有 `die_sysfs_probe.py` 是**这一接口的特化检查**，不是对任意 sysfs 属性的自动提取。跨版本工具/内核组合要单列。 |
| **2. 可表示页阶** | 对可达的 `PAGE_SHIFT`、`XA_CHUNK_SHIFT` 与大页策略组合求 `HPAGE_PMD_ORDER` 和 `MAX_PAGECACHE_ORDER`；只有可能选择 PMD 页时要求前者不大于后者，并定位选择门禁。 | 普通 4K 配置和禁用策略必须保持正常；64K 普通配置的启用策略应被拦截。现有 `shmem_pagecache_probe.py` 只验证已知函数，尚未自动发现其他入口，也未覆盖所有 Kconfig 可达组合。 |
| **后续：时序与设备边界** | 时序需有同一状态的 P/C、CPUHP 或调用图顺序、失败/下线关系；DMA 需确认非一致性与目标对齐；SMMU 需有模式化命令语义。缺一项输出“证据不足/人工复核”，不输出“无问题”。 | 在已知案例上分别有原型；v1/v2 文本搬移留出样本未找到目标阳性，不能用文本移动替代契约推导，也不能从这批目的性案例算精确率或召回率。 |

下一轮的可检验任务是先将前两项写成**接口专用但配置可枚举**的检查说明或规则输入，冻结“命中、正常、不适用、证据不足”的判定，再找**未用于制定规则的内核接口或提交**做源码复核。报告需分开记录候选提取、人工确认、真实构建/运行和误报；若新接口的能力来源或页阶消费者无法确定，明确停在证据不足，不因同名宏或相似标题推断。

## 当不同架构对接口的理解不一致时

矩阵为每条检查保留一个**按接口确定的权威来源**，不按多数架构实现投票：磁盘格式的几何值来自 superblock；页缓存选择受 xarray 可表示上限约束；这次历史 die sysfs 实现用两项架构原生宏及 SMP 条件决定是否导出，不能拿通用默认宏代替，也不能据此证明任意架构或版本的 die 硬件语义；热插拔时序由该阶段消费者实际读取的状态与 CPUHP 顺序约束；设备命令还需符合所用模式的编码语义。历史补丁说明与原型提供因果线索，但不足以自动决定 ABI 或硬件规范冲突时的正确策略。若规范、内核接口约定、架构能力或可达配置彼此冲突，就将该行标为**待领域裁定**，保存两边证据和正常反例，不生成全架构强制规则。

几个已知边界用来防止过度归纳：VT-d 二级页表的 WO 权限检查已有 QEMU/KUnit 支持，但一级页表 WO 仍不可表示，不能跨模式套用；RISC-V `capacity-dmips-mhz` 在当时不是有效 DT 属性，只作条件性时序机制；parisc 的时钟策略补丁后来撤销；NUMA native/compat 的历史完整入口链与剩余边界尚未裁定；perf 大端 union 案例属于用户态工具。它们保留在原台账中作反例或待核查项，不并入上述八条主矩阵。
